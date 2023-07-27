from time import sleep
from typing import Dict, List
import os.path

import numpy as np
import pickle


from asynfed.server.objects import Worker
from asynfed.server.storage_connectors.boto3 import ServerStorageBoto3
from asynfed.common.config import LocalStoragePath

from .strategy import Strategy

import sys

from threading import Lock
lock = Lock()


import logging
LOGGER = logging.getLogger(__name__)


from threading import Lock
from time import sleep
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


class Asyn2fStrategy(Strategy):

    # def __init__(self, server: Server, model_name: str, file_extension: str, m: int = 3):
    def __init__(self, server, model_name: str, file_extension: str, m: int = 1):
        super().__init__(server = server, model_name= model_name, file_extension= file_extension)
        self.m = m


    def start_server(self):
        if not self._server._config.strategy.update_period or self._server._config.strategy.update_period == 0:
            # constantly check for new udpate
            self._server._config.strategy.update_period = 2

        self._server._start_threads()

        while True:
            if self._server._stop_condition_is_met:
                LOGGER.info('Stop condition is reached! Shortly the training process will be close.')
                # close the program
                sys.exit(0)

            with lock:
                n_local_updates = len(self._server._worker_manager.get_completed_workers())

            if n_local_updates < self.m:
                sleep(self._server._config.strategy.update_period)

            else:
                try:
                    LOGGER.info(f'Update condition is met. Start update global model with {n_local_updates} local updates')
                    self._update(n_local_updates)
                    self._server._publish_new_global_model()

                except Exception as e:
                    raise e
                
    def _update(self, n_local_updates: int):
        if n_local_updates == 1:
            LOGGER.info("Only one update from client, passing the model to all other client in the network...")
            completed_worker: dict[str, Worker] = self._server._worker_manager.get_completed_workers()
            self._pass_one_local_model(completed_worker)

        else:
            LOGGER.info("Aggregating process...")
            completed_workers: dict[str, Worker] = self._server._worker_manager.get_completed_workers()
            
            # reset the state of worker in completed workers list
            for w_id, worker in completed_workers.items():
                worker.is_completed = False
                # keep track of the latest local version of worker used for cleaning task
                model_filename = worker.get_remote_weight_file_path().split(os.path.sep)[-1]
                worker.update_local_version_used = self.extract_model_version(model_filename)

            # pass out a copy of completed worker to aggregating process
            worker_list = copy.deepcopy(completed_workers)
            self.aggregate(worker_list, self._server._cloud_storage, self._server._local_storage_path)


    def _pass_one_local_model(self, completed_worker: Dict [str, Worker]):
        for w_id, worker in completed_worker.items():
            LOGGER.info(w_id)
            self.avg_loss = worker.loss
            self.avg_qod = worker.qod
            self.global_model_update_data_size = worker.data_size
            worker.is_completed = False

            # download worker weight file
            remote_weight_file = worker.get_remote_weight_file_path()
            local_weight_file = worker.get_local_weight_file_path(local_model_root_folder= self._local_storage_path.LOCAL_MODEL_ROOT_FOLDER)
            self._cloud_storage.download(remote_file_path= remote_weight_file, 
                                        local_file_path= local_weight_file)

            # keep track of the latest local version of worker used for cleaning task
            model_filename = local_weight_file.split(os.path.sep)[-1]
            worker.update_local_version_used = self.extract_model_version(model_filename)

        # copy the worker model weight to the global model folder
        save_location = os.path.join(self._server._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self.get_new_global_model_filename())
        shutil.copy(local_weight_file, save_location)




    def respond_connection(self, message: dict):
        message_utils.print_message(message)

        session_id, reconnect = self._server._check_client_identity_when_joining(message)
        client_id: str = message['headers']['client_id']
        access_key, secret_key = self._server._cloud_storage.get_client_key()


        # notify newest global model to worker
        model_url = self._server._cloud_storage.get_newest_global_model()

        # always use forward slash for the cloud storage regardless os
        model_version = self.extract_model_version(folder_path= model_url)

        # update the current version for the strategy 
        # if the server is just on the first round
        if self.current_version == None:
            self.current_version = model_version


        # model info
        exchange_at= self._server._config.model_config.model_exchange_at.to_dict()


        model_info: ModelInfo = ModelInfo(global_folder= self._server._config.cloud_storage.global_model_root_folder, 
                                          name= self._server._config.model_config.name, version=self.current_version,
                                          file_extension= self.file_extension, exchange_at= exchange_at)
        
        # check the correctness of message when sending
        message_utils.print_message(model_info.to_dict())

        client_folder = f"{self._server._cloud_storage_path.CLIENT_MODEL_ROOT_FOLDER}/{client_id}"
        # storage info
        storage_info: StorageInfo = StorageInfo(type= self._server._config.cloud_storage.type,
                                                access_key= access_key, secret_key= secret_key, 
                                                bucket_name= self._server._config.cloud_storage.bucket_name,
                                                region_name= self._server._config.cloud_storage.region_name,
                                                client_upload_folder= client_folder)
        if not self._server._aws_s3:
            storage_info.endpoint_url = self._server._config.cloud_storage.minio.endpoint_url


        # send message
        headers: dict = self._server._create_headers(message_type= MessageType.SERVER_INIT_RESPONSE)
        headers['session_id'] = session_id
        headers['reconnect'] = reconnect

        epoch_update_frequency = 5
        response_to_init: ServerRespondToInit = ServerRespondToInit(strategy= self._server._config.strategy.name,
                                                    epoch_update_frequency= epoch_update_frequency,
                                                    model_info= model_info.to_dict(),
                                                    storage_info= storage_info.to_dict())
        

        message_utils.print_message(response_to_init.to_dict())
        message= ExchangeMessage(headers= headers, content= response_to_init.to_dict()).to_json()
        self._server._queue_producer.send_data(message)



    def handle_client_notify_model(self, message):
        message_utils.print_message(message)
        client_id: str = message['headers']['client_id']

        client_model_update: ClientModelUpdate = ClientModelUpdate(**message['content'])

        # only update the remote local weight path, not download to the device
        self._server._worker_manager.add_local_update(client_id, client_model_update)

        # write to influx db
        # self._influxdb.write_training_process_data(timestamp, client_id, client_model_update)


    def handle_client_notify_evaluation(self, message):
        message_utils.print_message(message)
        model_evaluation: NotifyEvaluation = NotifyEvaluation(**message['content'])


        if model_evaluation.performance > self._server._best_model.performance:
            self._server._best_model.update(model_evaluation)
            self._server._write_record()

        model_evaluation.version = self.extract_model_version(model_evaluation.remote_storage_path)
        model_evaluation_dict = model_evaluation.to_dict()

        if self._server._check_stop_conditions(model_evaluation_dict):
            headers: dict = self._server._create_headers(message_type= MessageType.SERVER_STOP_TRAINING)
            require_to_stop: ServerRequestStop = ServerRequestStop()

            message = ExchangeMessage(headers= headers, content= require_to_stop.to_dict()).to_json()
            self._server._queue_producer.send_data(message)
            LOGGER.info("=" * 50)
            LOGGER.info("Stop condition met. Log out best model")
            LOGGER.info(self._server._best_model)
            LOGGER.info("=" * 50)

            self._server._stop_condition_is_met = True

        else:
            LOGGER.info(f"Up to testing global epoch {model_evaluation.version}. Best model is:")
            LOGGER.info(self._server._best_model)


    def handle_client_ping(self, message):
        message_utils.print_message(message)
        self._server._worker_manager.update_worker_last_ping(message['headers']['client_id'])


    def select_client(self, all_clients) -> List [str]:
        return all_clients
    

    def compute_alpha(self, worker: Worker) -> float:
        # avoid division by zero
        alpha  = worker.qod * worker.data_size / (worker.loss + 1e-7)
        alpha /= (self.update_version - worker.global_version_used)
        return alpha

    def aggregate(self, completed_workers: Dict [str, Worker], cloud_storage: ServerStorageBoto3, 
                  local_storage_path: LocalStoragePath):
        LOGGER.info("-" * 20)
        LOGGER.info(f"Current global version before aggregating process: {self.current_version}")
        LOGGER.info(f"{len(completed_workers)} workers are expected to join this aggregating round")
        LOGGER.info("-" * 20)

        LOGGER.info("Before aggregating takes place, check whether the file path that client provide actually exist in the cloud storage")
        completed_workers = self._get_valid_completed_workers(workers= completed_workers, 
                                                              cloud_storage= cloud_storage,
                                                              local_model_root_folder= local_storage_path.LOCAL_MODEL_ROOT_FOLDER)

        LOGGER.info(f"After checking for validity of remote file, the number of workers joining the aggregating process is now {len(completed_workers)}")
        LOGGER.info("*" * 20)

        # increment the current version
        self.update_version = self.current_version + 1
        # self.current_version += 1
        total_completed_worker = len(completed_workers)

        
        # calculate average quality of data, average loss and total datasize to notify client
        self.avg_qod = sum([worker.qod for w_id, worker in completed_workers.items()]) / total_completed_worker
        self.avg_loss = sum([worker.loss for w_id, worker in completed_workers.items()]) /  total_completed_worker
        self.global_model_update_data_size = sum([worker.data_size for w_id, worker in completed_workers.items()])
        LOGGER.info(f"Total data: {self.global_model_update_data_size}, avg_loss: {self.avg_loss}, avg_qod: {self.avg_qod}")

        # calculate alpha of each  worker
        sum_alpha = 0.0
        LOGGER.info("*" * 20)
        for w_id, worker in completed_workers.items():
            LOGGER.info(f"Update global version: {self.update_version}")
            LOGGER.info(f"worker id {worker.worker_id} with global version used {worker.global_version_used}")
            LOGGER.info(f"substract: {self.update_version - worker.global_version_used}")
            
            worker.alpha = self.compute_alpha(worker)
            sum_alpha += worker.alpha
        LOGGER.info("*" * 20)

        LOGGER.info("*" * 20)
        LOGGER.info("Alpha after being normalized")
        for w_id, worker in completed_workers.items():
            worker.alpha /= sum_alpha
            LOGGER.info(f"{w_id}: {worker.alpha}")
        LOGGER.info("*" * 20)


        # aggregating to get the new global weights
        merged_weights = None
        for w_id, worker in completed_workers.items():
            # initialized zero array if merged weight is None
            if merged_weights is None:
                # choose dtype = float 32 to reduce the size of the weight file
                merged_weights = [np.zeros(layer.shape, dtype=np.float32) for layer in worker.weight_array]

            # merging
            for merged_layer, worker_layer in zip(merged_weights, worker.weight_array):
                merged_layer += worker.alpha * worker_layer


        # save weight file.
        # increment here to begin upload the model
        save_location = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self.get_new_global_model_filename())

        with open(save_location, "wb") as f:
            pickle.dump(merged_weights, f)
        LOGGER.info('=' * 20)
        LOGGER.info(save_location)
        LOGGER.info('=' * 20)
        

    def _get_model_weights(self, file_path):
        while not os.path.isfile(file_path):
            LOGGER.info("*" * 20)
            LOGGER.info("Sleep 5 second when the the download process is not completed, then retry")
            LOGGER.info(file_path)
            LOGGER.info("*" * 20)
            sleep(5)

        with open(file_path, "rb") as f:
            weights = pickle.load(f)
            
        return weights
    

    def _get_valid_completed_workers(self, workers: Dict[str, Worker], cloud_storage: ServerStorageBoto3,
                                     local_model_root_folder: str) -> Dict[str, Worker]:
        valid_completed_workers = {}

        for w_id, worker in workers.items():
            remote_path = worker.get_remote_weight_file_path()
            LOGGER.info("*" * 20)
            LOGGER.info(f"{worker.worker_id} qod: {worker.qod}, loss: {worker.loss}, datasize : {worker.data_size}, weight file: {remote_path}")
            file_exists = cloud_storage.is_file_exists(file_path= remote_path)
            
            if file_exists:
                LOGGER.info(f"{remote_path} exists in the cloud. Begin to download shortly")
                local_path = worker.get_local_weight_file_path(local_model_root_folder= local_model_root_folder)
                download_success = self._attempt_to_download(cloud_storage= cloud_storage, 
                                                             remote_file_path= remote_path, local_file_path= local_path)
                
                if download_success:
                    worker.weight_array =  self._get_model_weights(local_path)
                    valid_completed_workers[w_id] = worker

            else:
                LOGGER.info(f"worker {w_id}: weight file {remote_path} does not exist in the cloud. Remove {w_id} from aggregating process")

            LOGGER.info("*" * 20)

        return valid_completed_workers



    def _attempt_to_download(self, cloud_storage: ServerStorageBoto3, remote_file_path: str, local_file_path: str) -> bool:
        LOGGER.info("Downloading new client model............")
        attemp = 3

        for i in range(attemp):
            if cloud_storage.download(remote_file_path= remote_file_path, 
                                            local_file_path= local_file_path, try_time= attemp):
                return True
            
            LOGGER.info(f"{i + 1} attempt: download model failed, retry in 5 seconds.")

            i += 1
            if i == attemp:
                LOGGER.info(f"Already try 3 time. Pass this client model: {remote_file_path}")
            sleep(5)

        return False