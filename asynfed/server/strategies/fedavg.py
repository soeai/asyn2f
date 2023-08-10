from time import sleep
from typing import Dict, List
import os.path

import numpy as np
import pickle
from typing import Dict

from asynfed.server.objects import Worker
from asynfed.server.storage_connectors.boto3 import ServerStorageBoto3
from asynfed.common.config import LocalStoragePath

from .strategy import Strategy
import copy
import sys

from threading import Lock
lock = Lock()


import logging
LOGGER = logging.getLogger(__name__)


from threading import Lock
from time import sleep
import logging
import os
import sys
from typing import Dict

# Third party imports
from asynfed.common.messages.client import ClientModelUpdate
import asynfed.common.messages as message_utils


class FedAvgStrategy(Strategy):

    # def __init__(self, server: Server, model_name: str, file_extension: str, m: int = 3):
    def __init__(self, server, total_update_times: int, initial_learning_rate: float,
                    model_name: str, file_extension: str, m: int = 1, 
                    use_loss: bool = False, beta: float = 0.5):
        super().__init__(server = server, total_update_times= total_update_times, initial_learning_rate= initial_learning_rate,
                         model_name= model_name, file_extension= file_extension)
        
        self.m = m

        # self.first_aggregating_time = True
        self.first_aggregating_time = False
        self.m = m

        self.use_loss = use_loss
        self.beta = beta or 0.5
        
        LOGGER.info("=" * 50)

        print(f"inside strategy: {self.use_loss}")
        if self.use_loss:
            LOGGER.info("For FedAvg, Server choose to use both loss and data size to compute weighted for aggregating process")
            LOGGER.info(f"This is the beta used: {self.beta}")
        else:
            LOGGER.info("For FedAvg, Server choose to use only data size to compute weighted for aggregating process")
        LOGGER.info("=" * 50)


        print(f"This is m: {self.m}")

    # def start_server(self):
    def handle_aggregating_process(self):
        sleep(240)
        if not self._server.config.strategy.update_period or self._server.config.strategy.update_period == 0:
            # constantly check for new udpate
            self._server.config.strategy.update_period = 20

        while True:
            if self._server.stop_condition_is_met:
                LOGGER.info('Stop condition is reached! The program will be close now..')
                # close the program
                sys.exit(0)

            num_completed_workers = len(self._server.worker_manager.get_completed_workers())
            ready =  num_completed_workers >= self.m
            print(num_completed_workers, ready)
            if ready:
                self._server.worker_manager.update_worker_connections()
                print(f"This is the number of connected worker: {len(self._server.worker_manager.list_connected_workers())}")
                connected_workers_complete = self._server.worker_manager.check_connected_workers_complete_status()

                print(f"Status of connected workers: {connected_workers_complete}")


                if connected_workers_complete or self.first_aggregating_time:
                    LOGGER.info(f"This is the number of worker expected to join this round {self.current_version}: {num_completed_workers}")
                    self.first_aggregating_time = False
                    try:
                        completed_workers: Dict [str, Worker] = self._server.worker_manager.get_completed_workers()
                        LOGGER.info(f'Update condition is met. Start update global model with {len(completed_workers)} local updates')
                        self._update(completed_workers)
                        # wait until m worker connected to the network to begin new training epoch
                        while True:
                            self._server.worker_manager.update_worker_connections()
                            if self._server.worker_manager.get_num_connected_workers() >= self.m:
                                print("About to publish new global model")
                                self._server.publish_new_global_model()
                                print("After publishing new global model")
                                self._server.worker_manager.reset_all_workers_training_state()
                                print("After reset state of worker")
                                break
                            sleep(self._server.config.strategy.update_period)

                    except Exception as e:
                        raise e
                else:
                    sleep(self._server.config.strategy.update_period)

            
            sleep(self._server.config.strategy.update_period)

                
    def _update(self, completed_workers: Dict [str, Worker]):
        LOGGER.info("Aggregating process...")
        
        # reset the state of worker in completed workers list
        for w_id, worker in completed_workers.items():
            worker.is_completed = False
            # keep track of the latest local version of worker used for cleaning task
            model_filename = worker.get_remote_weight_file_path().split(os.path.sep)[-1]
            worker.update_local_version_used = self.extract_model_version(model_filename)

        # pass out a copy of completed worker to aggregating process
        self.aggregate(completed_workers, self._server.local_storage_path)


    def handle_client_notify_model(self, message):
        message_utils.print_message(message)
        client_id: str = message['headers']['client_id']

        client_model_update: ClientModelUpdate = ClientModelUpdate(**message['content'])

        # update the state in the worker manager to clean storage
        # even if download model fail
        # still mark as is completed 
        # so that it does not block the server to aggregate
        # when aggregating, the other constrain is the weight array is not None
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

        # write to influx db
        # self._influxdb.write_training_process_data(timestamp, client_id, client_model_update)


    def select_client(self, all_clients) -> List [str]:
        return all_clients
    
    def _compute_alpha(self, worker: Worker) -> float:
        data_depend  = worker.data_size / self.global_model_update_data_size 

        if self.use_loss:
            # avoid division by zero
            loss_depend = worker.loss / self.total_loss
            alpha = data_depend * (1 - self.beta) + loss_depend * self.beta
        else:
            alpha = data_depend

        return alpha

    def aggregate(self, completed_workers: Dict [str, Worker], local_storage_path: LocalStoragePath):
        # dealing with a list of NumPy arrays of different shapes (each representing the weights of a different layer of a neural network). 
        # This kind of heterogeneous structure is not conducive to the vectorized operations that make NumPy efficient
        # loop through each layer in the list
        # more efficient than converting the entire list into a single 'object'-dtype NumPy array
        # aggregating to get the new global weights
        self.global_model_update_data_size = sum([worker.data_size for w_id, worker in completed_workers.items()])
        self.total_loss = sum([worker.loss for w_id, worker in completed_workers.items()])

        merged_weights = None

        for w_id, worker in completed_workers.items():
            worker.alpha = self._compute_alpha(worker)
            LOGGER.info(f"{w_id}, alpha: {worker.alpha}, data_size: {worker.data_size}, loss: {worker.loss}")

            if worker.weight_array is not None:
                LOGGER.info(f"{w_id}: {worker.data_size}, {worker.get_remote_weight_file_path()}, global version used: {worker.global_version_used}")
                # initialized zero array if merged weight is None
                if merged_weights is None:
                    # choose dtype = float 32 to reduce the size of the weight file
                    merged_weights = [np.zeros(layer.shape, dtype=np.float32) for layer in worker.weight_array]

                # self.com
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
        


