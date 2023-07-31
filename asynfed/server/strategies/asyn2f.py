from time import sleep
from typing import Dict, List
import os

import numpy as np
import pickle

import sys

from threading import Lock
lock = Lock()

import asynfed.common.utils.time_ultils as time_utils

from threading import Lock
from time import sleep
import copy
import logging
import os
import shutil
import sys
from typing import Dict

from asynfed.common.messages.client import ClientModelUpdate
import asynfed.common.messages as message_utils

from asynfed.server.objects import Worker
from asynfed.server.storage_connectors.boto3 import ServerStorageBoto3
from asynfed.common.config import LocalStoragePath


from .strategy import Strategy

import logging
LOGGER = logging.getLogger(__name__)

class Asyn2fStrategy(Strategy):

    # def __init__(self, server: Server, model_name: str, file_extension: str, m: int = 3):
    def __init__(self, server, total_update_times: int, initial_learning_rate: float,
                    model_name: str, file_extension: str, m: int = 1):
        super().__init__(server = server, total_update_times= total_update_times, initial_learning_rate= initial_learning_rate,
                         model_name= model_name, file_extension= file_extension)
        self.m = m


    def handle_aggregating_process(self):
        if not self._server.config.strategy.update_period or self._server.config.strategy.update_period == 0:
            # constantly check for new udpate
            self._server.config.strategy.update_period = 2

        while True:
            if self._server.stop_condition_is_met:
                LOGGER.info('Stop condition is reached! The program will be close now..')
                # close the program
                sys.exit(0)

            with lock:
                n_local_updates = len(self._server.worker_manager.get_completed_workers())

            if n_local_updates < self.m:
                sleep(self._server.config.strategy.update_period)

            else:
                try:
                    LOGGER.info(f'Update condition is met. Start update global model with {n_local_updates} local updates')
                    self._update(n_local_updates)
                    self._server.publish_new_global_model()

                except Exception as e:
                    raise e
                
    def _update(self, n_local_updates: int):
        if n_local_updates == 1:
            LOGGER.info("Only one update from client, passing the model to all other client in the network...")
            completed_worker: dict[str, Worker] = self._server.worker_manager.get_completed_workers()
            self._pass_one_local_model(completed_worker)

        else:
            LOGGER.info("Aggregating process...")
            completed_workers: dict[str, Worker] = self._server.worker_manager.get_completed_workers()
            
            # reset the state of worker in completed workers list
            for w_id, worker in completed_workers.items():
                worker.is_completed = False
                # keep track of the latest local version of worker used for cleaning task
                model_filename = worker.get_remote_weight_file_path().split(os.path.sep)[-1]
                worker.update_local_version_used = self.extract_model_version(model_filename)

            # pass out a copy of completed worker to aggregating process
            worker_list = copy.deepcopy(completed_workers)
            self.aggregate(worker_list, self._server.cloud_storage, self._server.local_storage_path)



    def _pass_one_local_model(self, completed_worker: Dict [str, Worker]):
        for w_id, worker in completed_worker.items():
            LOGGER.info(w_id)
            self.avg_loss = worker.loss
            self.avg_qod = worker.qod
            self.global_model_update_data_size = worker.data_size
            worker.is_completed = False

            # download worker weight file
            remote_weight_file = worker.get_remote_weight_file_path()
            local_weight_file = worker.get_local_weight_file_path(local_model_root_folder= self._server.local_storage_path.LOCAL_MODEL_ROOT_FOLDER)
            self._server.cloud_storage.download(remote_file_path= remote_weight_file, 
                                        local_file_path= local_weight_file)

            # keep track of the latest local version of worker used for cleaning task
            # model_filename = local_weight_file.split(os.path.sep)[-1]
            worker.update_local_version_used = self.extract_model_version(local_weight_file)

        # copy the worker model weight to the global model folder
        save_location = os.path.join(self._server.local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self.get_new_global_model_filename())
        shutil.copy(local_weight_file, save_location)



    def handle_client_notify_model(self, message):
        message_utils.print_message(message)
        client_id: str = message['headers']['client_id']

        client_model_update: ClientModelUpdate = ClientModelUpdate(**message['content'])

        # only update the remote local weight path, not download to the device
        self._server.worker_manager.add_local_update(client_id, client_model_update)

        # write to influx db
        # self._influxdb.write_training_process_data(timestamp, client_id, client_model_update)



    def select_client(self, all_clients) -> List [str]:
        return all_clients
    

    def _compute_alpha(self, worker: Worker) -> float:
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
            LOGGER.info(f"{worker.worker_id}: global version used: {worker.global_version_used}, qod: {worker.qod}, loss: {worker.loss}, datasize : {worker.data_size}")
            # LOGGER.info(f"worker id {worker.worker_id} with global version used {worker.global_version_used}")
            LOGGER.info(f"substract: {self.update_version - worker.global_version_used}")
            
            worker.alpha = self._compute_alpha(worker)
            sum_alpha += worker.alpha
        LOGGER.info("*" * 20)

        LOGGER.info("*" * 20)
        LOGGER.info("Alpha after being normalized")
        for w_id, worker in completed_workers.items():
            worker.alpha /= sum_alpha
            LOGGER.info(f"{w_id}: {worker.alpha}")
        LOGGER.info("*" * 20)


        # dealing with a list of NumPy arrays of different shapes (each representing the weights of a different layer of a neural network). 
        # This kind of heterogeneous structure is not conducive to the vectorized operations that make NumPy efficient
        # loop through each layer in the list
        # more efficient than converting the entire list into a single 'object'-dtype NumPy array
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



