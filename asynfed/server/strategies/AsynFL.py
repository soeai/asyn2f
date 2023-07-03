import os.path
from copy import copy
from typing import List, Dict

import numpy as np
from numpy import ndarray
import pickle

from asynfed.commons.conf import Config
from asynfed.server.objects import Worker
from asynfed.server.strategies import Strategy

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
        return alpha

    def aggregate(self, worker_manager: WorkerManager, cloud_storage):
    # def aggregate(self, worker_manager: WorkerManager, cloud_storage: ServerStorage):
        # calculate avg, loss and datasize here
        # Get all workers that has the weight version with server
        LOGGER.info("-" * 20)
        LOGGER.info(f"Current global version before aggregating process: {self.current_version}")
        LOGGER.info("-" * 20)
        self.current_version += 1
        completed_workers: dict[str, Worker] = worker_manager.get_completed_workers()
        total_completed_worker = len(completed_workers)

        # calculate average quality of data, average loss and total datasize to notify client
        self.avg_qod = sum([worker.qod for w_id, worker in completed_workers.items()]) / total_completed_worker
        self.avg_loss = sum([worker.loss for w_id, worker in completed_workers.items()]) /  total_completed_worker
        self.global_model_update_data_size = sum([worker.data_size for w_id, worker in completed_workers.items()])

        sum_alpha = 0.0
        LOGGER.info("*" * 20)
        for w_id, worker in completed_workers.items():
            # worker.alpha = self.compute_alpha(worker)
            LOGGER.info(f"{worker.worker_id} qod: {worker.qod}, loss: {worker.loss}, datasize : {worker.data_size}")
            # reset state after update
        LOGGER.info("*" * 20)
        
        # print("Alpha before being normalized")
        for w_id, worker in completed_workers.items():
            worker.alpha = self.compute_alpha(worker)
            sum_alpha += worker.alpha
            worker.is_completed = False
        #     print(f"{worker.worker_id} with alpha {worker.alpha}, qod: {worker.qod}, loss: {worker.loss}, datasize : {worker.data_size}")
        #     sum_alpha += worker.alpha
            # reset state after update

        LOGGER.info(f"Total data: {self.global_model_update_data_size}, avg_loss: {self.avg_loss}, avg_qod: {self.avg_qod}")
        # print("*" * 20)


        LOGGER.info("*" * 20)
        LOGGER.info("Alpha after being normalized")
        for w_id, worker in completed_workers.items():
            worker.alpha /= sum_alpha
            LOGGER.info(f"{w_id}: {worker.alpha}")
        LOGGER.info("*" * 20)

        # Create a new weight with the same shape and type as a given weight.
        merged_weight = None
        for cli_id, worker in completed_workers.items():
            LOGGER.info("*" * 20)
            # download only when aggregating
            worker_current_version = worker.current_version
            remote_weight_file = worker.get_remote_weight_file_path()
            local_weight_file = worker.get_weight_file_path()
            cloud_storage.download(remote_file_path= remote_weight_file, 
                                        local_file_path= local_weight_file)
            
            # weight_file = worker.get_weight_file_path()

            # Load the array from the specified file using the numpy.load function
            weight = self.get_model_weights(local_weight_file)

            if merged_weight is None:
                merged_weight = copy(weight)
            else:
                LOGGER.info(f"Current global version: {self.current_version}")
                LOGGER.info(f"worker id {worker.worker_id} with global version used {worker_current_version}")
                LOGGER.info(f"substract: {self.current_version - worker_current_version}")
                for layers in range(len(weight)):
                    merged_weight[layers] += 1 / total_completed_worker * (
                            worker.alpha / (self.current_version - worker_current_version)) * \
                                             weight[layers]
            LOGGER.info("*" * 20)

        # save weight file.
        save_location = Config.TMP_GLOBAL_MODEL_FOLDER + self.get_global_model_filename()
        LOGGER.info(save_location)
        LOGGER.info('=' * 20)
        with open(save_location, "wb") as f:
            pickle.dump(merged_weight, f)
        # print(merged_weight)
        

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

