
# Standard library imports
from threading import Lock
from time import sleep
import concurrent.futures
import copy
import logging
import os
import shutil
import sys
from typing import Dict

# Third party imports
from asynfed.common.config import MessageType
from asynfed.common.messages import ExchangeMessage
from asynfed.common.messages.client import ClientModelUpdate, NotifyEvaluation, TesterRequestStop
from asynfed.common.messages.server import ServerRequestStop
from asynfed.common.messages.server.server_response_to_init import ServerRespondToInit, ModelInfo, StorageInfo
import asynfed.common.messages as message_utils

# Local imports
from asynfed.server.objects import Worker
from asynfed.server import Server


thread_pool_ref = concurrent.futures.ThreadPoolExecutor
lock = Lock()

LOGGER = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
LOGGER.setLevel(logging.INFO)


class Asyn2fServer(Server):
    def __init__(self, config: dict):
        super().__init__(config)
        if not self._config.strategy.update_period or self._config.strategy.update_period == 0:
            # constantly check for new udpate
            self._config.strategy.update_period = 2

    def start(self):
        self._start_threads()

        while True:
            if self._stop_condition_is_met:
                LOGGER.info('Stop condition is reached! Shortly the training process will be close.')
                # close the program
                sys.exit(0)

            with lock:
                n_local_updates = len(self._worker_manager.get_completed_workers())

            if n_local_updates < self._config.strategy.m:
                sleep(self._config.strategy.update_period)

            else:
                try:
                    LOGGER.info(f'Update condition is met. Start update global model with {n_local_updates} local updates')
                    self._update(n_local_updates)
                    self._publish_new_global_model()

                except Exception as e:
                    raise e


    def _respond_connection(self, msg_received: dict):
        message_utils.print_message(msg_received)

        session_id, reconnect = self._check_client_identity_when_joining(msg_received= message)
        client_id: str = msg_received['headers']['client_id']
        access_key, secret_key = self._cloud_storage.get_client_key(client_id)


        # notify newest global model to worker
        model_url = self._cloud_storage.get_newest_global_model()
        # always use forward slash for the cloud storage regardless os
        model_version = self._strategy.extract_model_version(folder_path= model_url)
        
        # update the current version for the strategy 
        # if the server is just on the first round
        if self._strategy.current_version == None:
            self._strategy.current_version = model_version


        # model info
        exchange_at= self._config.model_config.model_exchange_at.to_dict()


        model_info: ModelInfo = ModelInfo(global_folder= self._cloud_storage_path.GLOBAL_MODEL_ROOT_FOLDER, 
                                          name= self._config.model_name, version=self._strategy.current_version,
                                          file_extension= self._strategy.file_extension, exchange_at= exchange_at)
        
        # check the correctness of message when sending
        message_utils.print_message(model_info.to_dict())

        client_folder = f"{self._cloud_storage_path.CLIENT_MODEL_ROOT_FOLDER}/{client_id}"
        # storage info
        storage_info: StorageInfo = StorageInfo(type= self._config.cloud_storage.type,
                                                access_key= access_key, secret_key= secret_key, 
                                                bucket_name= self._config.cloud_storage.bucket_name,
                                                region_name= self._config.cloud_storage.region_name,
                                                client_upload_folder= client_folder)
        if not self._aws_s3:
            storage_info.endpoint_url = self._config.cloud_storage.minio.endpoint_url


        # send message
        headers: dict = self._create_headers(message_type= MessageType.SERVER_INIT_RESPONSE)
        headers['session_id'] = session_id
        headers['reconnect'] = reconnect

        response_to_init: ServerRespondToInit = ServerRespondToInit(strategy= self._config.strategy.name,
                                                    model_info= model_info.to_dict(),
                                                    storage_info= storage_info.to_dict())
        

        message_utils.print_message(response_to_init.to_dict())
        message= ExchangeMessage(headers= headers, content= response_to_init.to_dict()).to_json()
        self._queue_producer.send_data(message)


    def _handle_client_notify_model(self, msg_received):
        message_utils.print_message(msg_received)
        client_id: str = msg_received['headers']['client_id']

        client_model_update: ClientModelUpdate = ClientModelUpdate(**msg_received['content'])

        # only update the remote local weight path, not download to the device
        self._worker_manager.add_local_update(client_id, client_model_update)

        # write to influx db
        # self._influxdb.write_training_process_data(timestamp, client_id, client_model_update)


    def _handle_client_notify_evaluation(self, msg_received):
        message_utils.print_message(msg_received)
        model_evaluation: NotifyEvaluation = NotifyEvaluation(**msg_received['content'])


        if model_evaluation.performance > self._best_model.performance:
            self._best_model.update(model_evaluation)
            self._write_record()

        model_evaluation.version = self._strategy.extract_model_version(model_evaluation.remote_storage_path)
        model_evaluation_dict = model_evaluation.to_dict()

        if self._check_stop_conditions(model_evaluation_dict):
            headers: dict = self._create_headers(message_type= MessageType.SERVER_STOP_TRAINING)
            require_to_stop: ServerRequestStop = ServerRequestStop()

            message = ExchangeMessage(headers= headers, content= require_to_stop.to_dict()).to_json()
            self._queue_producer.send_data(message)
            LOGGER.info("=" * 50)
            LOGGER.info("Stop condition met. Log out best model")
            LOGGER.info(self._best_model)
            LOGGER.info("=" * 50)

            self._stop_condition_is_met = True

        else:
            LOGGER.info(f"Up to testing global epoch {model_evaluation.version}. Best model is:")
            LOGGER.info(self._best_model)


    def _handle_client_ping(self, message):
        message_utils.print_message(message)
        self._worker_manager.update_worker_last_ping(message['headers']['client_id'])

    


    def _update(self, n_local_updates):
        if n_local_updates == 1:
            LOGGER.info("Only one update from client, passing the model to all other client in the network...")
            completed_worker: dict[str, Worker] = self._worker_manager.get_completed_workers()
            self._pass_one_local_model(completed_worker)

        else:
            LOGGER.info("Aggregating process...")
            completed_workers: dict[str, Worker] = self._worker_manager.get_completed_workers()
            
            # reset the state of worker in completed workers list
            for w_id, worker in completed_workers.items():
                worker.is_completed = False
                # keep track of the latest local version of worker used for cleaning task
                model_filename = worker.get_remote_weight_file_path().split(os.path.sep)[-1]
                worker.update_local_version_used = self._strategy.extract_model_version(model_filename)

            # pass out a copy of completed worker to aggregating process
            worker_list = copy.deepcopy(completed_workers)
            self._strategy.aggregate(worker_list, self._cloud_storage, self._local_storage_path)



    def _pass_one_local_model(self, completed_worker: Dict [str, Worker]):
        for w_id, worker in completed_worker.items():
            LOGGER.info(w_id)
            self._strategy.avg_loss = worker.loss
            self._strategy.avg_qod = worker.qod
            self._strategy.global_model_update_data_size = worker.data_size
            worker.is_completed = False

            # download worker weight file
            remote_weight_file = worker.get_remote_weight_file_path()
            local_weight_file = worker.get_weight_file_path(local_model_root_folder= self._local_storage_path.LOCAL_MODEL_ROOT_FOLDER)
            self._cloud_storage.download(remote_file_path= remote_weight_file, 
                                        local_file_path= local_weight_file)

            # keep track of the latest local version of worker used for cleaning task
            model_filename = local_weight_file.split(os.path.sep)[-1]
            worker.update_local_version_used = self._strategy.extract_model_version(model_filename)

        # copy the worker model weight to the global model folder
        save_location = os.path.join(self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self._strategy.get_new_global_model_filename())
        shutil.copy(local_weight_file, save_location)
