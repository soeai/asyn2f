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


class AsynFL(Strategy):

    def __init__(self):
        super().__init__()
        self.alpha: Dict = {}

    def select_client(self, all_clients) -> List[str]:
        return all_clients

    def compute_alpha(self, worker: Worker) -> float:
        alpha  = worker.qod.value * worker.data_desc.data_size / worker.loss
        return alpha

    def aggregate(self, worker_manager: WorkerManager):
        # calculate avg, loss and datasize here
        # Get all workers that has the weight version with server
        completed_workers: dict[str, Worker] = worker_manager.get_completed_workers()
        self.current_version += 1

        total_completed_worker = len(completed_workers)
        # calculate average quality of data, average loss and total datasize to notify client
        self.avg_qod = sum([completed_workers[w_id].qod.value for w_id in completed_workers]) / total_completed_worker
        self.avg_loss = sum([completed_workers[w_id].loss for w_id in completed_workers]) /  total_completed_worker
        self.global_model_update_data_size = sum([completed_workers[w_id].data_desc.data_size for w_id in completed_workers])

        # calculate alpha for aggregating process
        sum_alpha = 0
        for w_id, worker in completed_workers.items():
            worker.alpha = self.compute_alpha(worker)
            sum_alpha += worker.alpha

        for w_id, worker in completed_workers.items():
            worker.alpha /= sum_alpha


        # Create a new weight with the same shape and type as a given weight.
        merged_weight = None
        for cli_id, worker in completed_workers.items():
            weight_file = worker.get_weight_file_path()

            # Load the array from the specified file using the numpy.load function
            weight = self.get_model_weights(weight_file)

            if merged_weight is None:
                merged_weight = copy(weight)
            else:
                for layers in range(len(weight)):
                    merged_weight[layers] += 1 / total_completed_worker * (
                            worker.alpha / (self.current_version - worker.current_version)) * \
                                             weight[layers]

        # save weight file.
        save_location = Config.TMP_GLOBAL_MODEL_FOLDER + self.get_global_model_filename()
        print(save_location)
        print('=' * 20)
        with open(save_location, "wb") as f:
            pickle.dump(merged_weight, f)
        # print(merged_weight)

        

    def get_model_weights(self, file_path) -> ndarray:
        print("*" * 10)
        print(file_path)
        print("*" * 10)

        if os.path.isfile(file_path) is False:
            raise Exception("File not found")
        else:
            # return np.load(filepath, allow_pickle=True)
            with open(file_path, "rb") as f:
                weights = pickle.load(f)
            return weights

    def is_completed(self):
        return False
