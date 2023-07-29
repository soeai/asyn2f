from time import sleep
from typing import Dict, List
import os

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
import collections

# Third party imports
from asynfed.common.messages.client import ClientModelUpdate
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


    def handle_aggregating_process(self):
        if not self._server.config.strategy.update_period or self._server.config.strategy.update_period == 0:
            # constantly check for new udpate
            self._server.config.strategy.update_period = 2

        while True:
            if self._server.stop_condition_is_met:
                LOGGER.info('Stop condition is reached! Shortly the training process will be close.')
                # close the program
                sys.exit(0)

            total_local_models = len(self.model_queue)
            if total_local_models < self.m:
                sleep(self._server.config.strategy.update_period)

            else:
                try:
                    LOGGER.info("*" * 20)
                    LOGGER.info(f'In the attempt to aggregate new global version {self.current_version}, the number of models in the queue is {total_local_models}')
                    LOGGER.info(f'Update condition is met. Start update global model with {self.m} local updates')
                    LOGGER.info("*" * 20)
                    self._update()
                    self._server.publish_new_global_model()

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

        self.aggregate(worker_models, self._server.cloud_storage, self._server.local_storage_path)



    # implement a queue to store all model that pass through
    def handle_client_notify_model(self, message):
        message_utils.print_message(message)
        client_id: str = message['headers']['client_id']

        client_model_update: ClientModelUpdate = ClientModelUpdate(**message['content'])

        # update the state in the worker manager to clean storage
        self._server.worker_manager.add_local_update(client_id, client_model_update)


        worker: Worker = self._server.worker_manager.get_worker_by_id(client_id)
        remote_path = worker.get_remote_weight_file_path()
        file_exists = self._server.cloud_storage.is_file_exists(file_path= remote_path)
        if file_exists:
            LOGGER.info(f"{remote_path} exists in the cloud. Begin to download shortly")
            local_path = worker.get_local_weight_file_path(local_model_root_folder= self._server.local_storage_path.LOCAL_MODEL_ROOT_FOLDER)
            download_success = self._attempt_to_download(cloud_storage= self._server.cloud_storage, 
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


    def select_client(self, all_clients) -> List [str]:
        return all_clients
    

    def aggregate(self, workers: List [Worker], cloud_storage: ServerStorageBoto3,
                  local_storage_path: LocalStoragePath):


        if self.current_version == 1:
            local_path = self._server.config.model_config.initial_model_path
        else:
            local_path = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self.get_current_global_model_filename())

        # dealing with a list of NumPy arrays of different shapes (each representing the weights of a different layer of a neural network). 
        # This kind of heterogeneous structure is not conducive to the vectorized operations that make NumPy efficient
        # loop through each layer in the list
        # more efficient than converting the entire list into a single 'object'-dtype NumPy array
        # previous_global_weight = self._get_model_weights(local_path)

        # aggregate_global_weight = [np.zeros(layer.shape, dtype=np.float32) for layer in previous_global_weight]
        # total_data_size = sum([worker.data_size for worker in workers])

        # for worker in workers:
        #     LOGGER.info(f"{worker.worker_id}: {worker.data_size}, {worker.get_remote_weight_file_path()}")
        #     for aggregate_global_layer, worker_layer, previous_global_layer in zip(aggregate_global_weight, worker.weight_array, previous_global_weight):
        #         current_round_contribution = np.zeros(worker_layer.shape, dtype= np.float32)
        #         current_round_contribution += worker_layer * ( worker.data_size / total_data_size )
        #         aggregate_global_layer += current_round_contribution * self.agg_hyperparam + previous_global_layer * (1 - self.agg_hyperparam)

        # # save weight file.
        # save_location = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self.get_new_global_model_filename())

        # with open(save_location, "wb") as f:
        #     pickle.dump(aggregate_global_weight, f)

        total_num_samples = sum([worker.data_size for worker in workers])
        w_g = np.array(self._get_model_weights(local_path), dtype=object)
        w_new = np.array([np.zeros(layer.shape) for layer in w_g], dtype=object)

        for worker in workers:
            LOGGER.info(f"{worker.worker_id}: {worker.data_size}, {worker.get_remote_weight_file_path()}")
            worker_array = np.array(worker.weight_array, dtype=object)
            worker_weighted = worker.data_size / total_num_samples
            w_new += (worker_array * worker_weighted)

        ## Calculate w_g(t+1)
        w_g_new = w_g * (1-self.agg_hyperparam) + w_new * self.agg_hyperparam

        save_location = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self.get_new_global_model_filename())

        with open(save_location, "wb") as f:
            pickle.dump(w_g_new, f)

        LOGGER.info('=' * 20)
        LOGGER.info(save_location)
        LOGGER.info('=' * 20)
        
