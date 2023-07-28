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
import sys
from typing import Dict
import collections

# Third party imports
from asynfed.common.config import MessageType
from asynfed.common.messages import ExchangeMessage
from asynfed.common.messages.client import ClientModelUpdate, NotifyEvaluation, TesterRequestStop
from asynfed.common.messages.server import ServerRequestStop
from asynfed.common.messages.server.server_response_to_init import ServerRespondToInit, ModelInfo, StorageInfo
import asynfed.common.messages as message_utils


# from asynfed.server import Server
class KAFLMStepStrategy(Strategy):

    # def __init__(self, server: Server, model_name: str, file_extension: str, m: int = 3, agg_hyperparam: float = 0.8):
    def __init__(self, server, model_name: str, file_extension: str, m: int = 3, agg_hyperparam: float = 0.8):
        """
        Args:
            m (int, optional): Number of workers to aggregate. Defaults to 3.
            agg_hyperparam (float, optional): Aggregation hyperparameter. Defaults to 0.8.
        """
        super().__init__(server = server, model_name= model_name, file_extension= file_extension)
        self.m = m
        self.agg_hyperparam = agg_hyperparam
        # create a queue to store all the model get from client, 
        # regardless of whether within each update 
        # these model come from the same worker
        self.model_queue = collections.deque()


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

            total_local_models = len(self.model_queue)
            if total_local_models < self.m:
                sleep(self._server._config.strategy.update_period)

            else:
                try:
                    LOGGER.info(f'Update condition is met. Start update global model with {self.m} local updates')
                    self._update()
                    self._server._publish_new_global_model()

                except Exception as e:
                    raise e
                

    def _get_m_local_model(self):
        worker_models = []
        for _ in range(self.m):
            worker_models.append(self.model_queue.popleft())
        return worker_models

    def _update(self):
        LOGGER.info("Aggregating process...")
        worker_models: list = self._get_m_local_model()

        self.aggregate(worker_models, self._server._cloud_storage, self._server._local_storage_path)



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
        headers['client_id'] = client_id

        response_to_init: ServerRespondToInit = ServerRespondToInit(strategy= self._server._config.strategy.name,
                                                    epoch_update_frequency= self._server._config.strategy.n,
                                                    model_info= model_info.to_dict(),
                                                    storage_info= storage_info.to_dict())
        

        message_utils.print_message(response_to_init.to_dict())
        message= ExchangeMessage(headers= headers, content= response_to_init.to_dict()).to_json()
        self._server._queue_producer.send_data(message)



    # differ from asyn2f
    # implement a queue to store all model that pass through
    def handle_client_notify_model(self, message):
        message_utils.print_message(message)
        client_id: str = message['headers']['client_id']

        client_model_update: ClientModelUpdate = ClientModelUpdate(**message['content'])

        # update the state in the worker manager to clean storage
        self._server._worker_manager.add_local_update(client_id, client_model_update)


        worker: Worker = self._server._worker_manager.get_worker_by_id(client_id)
        remote_path = worker.get_remote_weight_file_path()
        file_exists = self._server._cloud_storage.is_file_exists(file_path= remote_path)
        if file_exists:
            LOGGER.info(f"{remote_path} exists in the cloud. Begin to download shortly")
            local_path = worker.get_local_weight_file_path(local_model_root_folder= self._server._local_storage_path.LOCAL_MODEL_ROOT_FOLDER)
            download_success = self._attempt_to_download(cloud_storage= self._server._cloud_storage, 
                                                            remote_file_path= remote_path, local_file_path= local_path)
            if download_success:
                worker.weight_array =  self._get_model_weights(local_path)
                model_filename = worker.get_remote_weight_file_path().split(os.path.sep)[-1]
                worker.update_local_version_used = self.extract_model_version(model_filename)

                # enqueue a copy of worker to model queue
                clone_worker = copy.deepcopy(worker)

                self.model_queue.append(clone_worker)


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
    

    # also differ here
    def aggregate(self, workers: List [Worker], cloud_storage: ServerStorageBoto3,
                  local_storage_path: LocalStoragePath):

        remote_path = cloud_storage.get_newest_global_model()
        filename = remote_path.split(os.path.sep)[-1]
        local_path = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, filename)
        if not os.path.exists(local_path):
            cloud_storage.download(remote_file_path=remote_path, local_file_path=local_path)
        w_g = np.array(self._get_model_weights(local_path))
        # Execute global update 
        ## Calculate w_new(t)
        w_new = 0
        w_tmp = []
        for i in range(len(workers)):
            w_i = np.array(self._get_model_weights(workers[i].get_local_weight_file_path(local_model_root_folder=local_storage_path.LOCAL_MODEL_ROOT_FOLDER)))
            w_tmp.append(w_i)
            w_new += (w_tmp[i]* workers[i].data_size)
        total_num_samples = sum([workers[i].data_size for i in range(len(workers))])
        w_new /= total_num_samples

        ## Calculate w_g(t+1)
        w_g_new = w_g * (1-self.agg_hyperparam) + w_new * self.agg_hyperparam
        

        # save weight file.
        save_location = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self.get_new_global_model_filename())

        with open(save_location, "wb") as f:
            pickle.dump(w_g_new, f)
        LOGGER.info('=' * 20)
        LOGGER.info(save_location)
        LOGGER.info('=' * 20)
        
