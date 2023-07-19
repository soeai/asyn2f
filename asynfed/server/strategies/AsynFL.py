from time import sleep
from typing import Dict, List
import os.path

import numpy as np
from numpy import ndarray
import pickle


from asynfed.server.objects import Worker
from asynfed.server.server_boto3_storage_connector import ServerStorageBoto3
from asynfed.commons.config import LocalStoragePath

from .strategy import Strategy


import logging
LOGGER = logging.getLogger(__name__)

class AsynFL(Strategy):

    def __init__(self):
        super().__init__()

    def select_client(self, all_clients) -> List [str]:
        return all_clients

    def compute_alpha(self, worker: Worker) -> float:
        # avoid division by zero
        alpha  = worker.qod * worker.data_size / (worker.loss + 1e-7)
        alpha /= (self.update_version - worker.current_version)
        return alpha

    def aggregate(self, completed_workers: Dict [str, Worker], cloud_storage: ServerStorageBoto3, 
                  local_storage_path: LocalStoragePath):
        LOGGER.info("-" * 20)
        LOGGER.info(f"Current global version before aggregating process: {self.current_version}")
        LOGGER.info("-" * 20)

        # increment the current version
        self.update_version = self.current_version + 1
        # self.current_version += 1
        total_completed_worker = len(completed_workers)

        # log out worker info
        LOGGER.info("*" * 20)
        for w_id, worker in completed_workers.items():
            LOGGER.info(f"{worker.worker_id} qod: {worker.qod}, loss: {worker.loss}, datasize : {worker.data_size}")
        LOGGER.info("*" * 20)
        
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
            LOGGER.info(f"worker id {worker.worker_id} with global version used {worker.current_version}")
            LOGGER.info(f"substract: {self.update_version - worker.current_version}")
            
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
            # download only when aggregating
            remote_weight_file = worker.get_remote_weight_file_path()
            local_weight_file = worker.get_weight_file_path(local_storage_path.LOCAL_MODEL_ROOT_FOLDER)

            cloud_storage.download(remote_file_path= remote_weight_file, 
                                        local_file_path= local_weight_file)
            
            # Load the weight from file
            worker_weights = self._get_model_weights(local_weight_file)

            # initialized zero array if merged weight is None
            if merged_weights is None:
                # choose dtype = float 32 to reduce the size of the weight file
                merged_weights = [np.zeros(layer.shape, dtype=np.float32) for layer in worker_weights]

            # merging
            for merged_layer, worker_layer in zip(merged_weights, worker_weights):
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
    
