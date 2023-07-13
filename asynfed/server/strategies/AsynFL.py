import os.path
from copy import copy
from typing import List, Dict

import numpy as np
from numpy import ndarray
import pickle

from asynfed.commons.conf import Config
from asynfed.server.objects import Worker
# from .Strategy import Strategy

from .strategy import Strategy

from asynfed.server.worker_manager import WorkerManager

from time import sleep
import logging
LOGGER = logging.getLogger(__name__)

class AsynFL(Strategy):

    def __init__(self):
        super().__init__()

    def select_client(self, all_clients) -> List[str]:
        return all_clients

    def compute_alpha(self, worker: Worker) -> float:
        # avoid division by zero
        alpha  = worker.qod * worker.data_size / (worker.loss + 1e-7)
        alpha /= (self.current_version - worker.current_version)
        # alpha = alpha / (self.current_version - worker.current_version)
        return alpha

    # def aggregate(self, worker_manager: WorkerManager, cloud_storage):
    # def aggregate(self, completed_workers: Dict[str, Worker], cloud_storage):
    def aggregate(self, completed_workers: dict[str, Worker], cloud_storage):
    # def aggregate(self, worker_manager: WorkerManager, cloud_storage: ServerStorage):
        # calculate avg, loss and datasize here
        # Get all workers that has the weight version with server
        LOGGER.info("-" * 20)
        LOGGER.info(f"Current global version before aggregating process: {self.current_version}")
        LOGGER.info("-" * 20)

        self.current_version += 1
        total_completed_worker = len(completed_workers)


        # update the state of worker so that when there is new message, 
        # it wait for the aggregating process to end
        LOGGER.info("*" * 20)
        for w_id, worker in completed_workers.items():
            # update aggregating state to freeze the updating info when receiving message from client
            # worker.is_aggregating = True
            # reset completed state 
            # worker.is_completed = False
            LOGGER.info(f"{worker.worker_id} qod: {worker.qod}, loss: {worker.loss}, datasize : {worker.data_size}")
        LOGGER.info("*" * 20)
        
        # calculate average quality of data, average loss and total datasize to notify client
        self.avg_qod = sum([worker.qod for w_id, worker in completed_workers.items()]) / total_completed_worker
        self.avg_loss = sum([worker.loss for w_id, worker in completed_workers.items()]) /  total_completed_worker
        self.global_model_update_data_size = sum([worker.data_size for w_id, worker in completed_workers.items()])

        sum_alpha = 0.0

        LOGGER.info(f"Total data: {self.global_model_update_data_size}, avg_loss: {self.avg_loss}, avg_qod: {self.avg_qod}")

        # print("Alpha before being normalized")
        for w_id, worker in completed_workers.items():
            LOGGER.info(f"Current global version: {self.current_version}")
            LOGGER.info(f"worker id {worker.worker_id} with global version used {worker.current_version}")
            LOGGER.info(f"substract: {self.current_version - worker.current_version}")
            
            worker.alpha = self.compute_alpha(worker)
            sum_alpha += worker.alpha



        LOGGER.info("*" * 20)
        LOGGER.info("Alpha after being normalized")
        for w_id, worker in completed_workers.items():
            worker.alpha /= sum_alpha
            LOGGER.info(f"{w_id}: {worker.alpha}")
        LOGGER.info("*" * 20)

        # # save the info of local and remote weight file of each worker
        # # then update the aggregating state for worker
        # # to allow it to continue update state 
        # # when receiving local model notify from client
        # aggregating_info = []
        # for w_id, worker in completed_workers.items():
        #     remote_weight_file = worker.get_remote_weight_file_path()
        #     local_weight_file = worker.get_weight_file_path()
        #     alpha = worker.alpha
        #     # update the state
        #     worker.is_aggregating = False
        #     aggregating_info.append((remote_weight_file, local_weight_file, alpha))


        # merged_weight = None
        # for remote_weight_file, local_weight_file, alpha in aggregating_info:
        #     cloud_storage.download(remote_file_path= remote_weight_file, 
        #                     local_file_path= local_weight_file)

        #     worker_weights = self.get_model_weights(local_weight_file)

        #     # initialized zero array if merged weight is None
        #     if merged_weight is None:
        #         merged_weight = [np.zeros(layer.shape) for layer in worker_weights]

        #     for i, layer in enumerate(worker_weights):
        #         merged_weight[i] += alpha * layer

        # download weight of each worker
        for w_id, worker in completed_workers.items():
            # download only when aggregating
            remote_weight_file = worker.get_remote_weight_file_path()
            local_weight_file = worker.get_weight_file_path()

            # # update the state of worker 
            # worker.is_aggregating = False

            cloud_storage.download(remote_file_path= remote_weight_file, 
                                        local_file_path= local_weight_file)
            
            # Load the array from the specified file using the numpy.load function
            worker_weights = self.get_model_weights(local_weight_file)

            # initialized zero array if merged weight is None
            if merged_weight is None:
                merged_weight = [np.zeros(layer.shape, dtype=np.float32) for layer in worker_weights]

            for i, layer in enumerate(worker_weights):
                merged_weight[i] += worker.alpha * layer


        # save weight file.
        save_location = Config.TMP_GLOBAL_MODEL_FOLDER + self.get_global_model_filename()
        LOGGER.info(save_location)
        LOGGER.info('=' * 20)
        with open(save_location, "wb") as f:
            pickle.dump(merged_weight, f)
        

    def get_model_weights(self, file_path) -> ndarray:
        LOGGER.info("*" * 10)
        LOGGER.info(file_path)
        LOGGER.info("*" * 10)

        while not os.path.isfile(file_path):
            LOGGER.info("*" * 20)
            sleep(5)
            LOGGER.info("Sleep 5 second when the model is not ready, then retry")
            LOGGER.info("*" * 20)

        with open(file_path, "rb") as f:
            weights = pickle.load(f)
        return weights

    def is_completed(self):
        return False
