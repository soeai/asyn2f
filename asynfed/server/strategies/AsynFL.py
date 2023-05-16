import os.path
from copy import copy
from typing import List, Dict

import numpy as np
from numpy import ndarray
import pickle

from asynfed.commons.conf   import Config
from asynfed.server.objects import Worker
from asynfed.server.strategies import Strategy

from asynfed.server.worker_manager import WorkerManager


class AsynFL(Strategy):
    def __init__(self):
        super().__init__()
        self.alpha: Dict = {}

    def get_global_model_filename(self):
        return f"{self.model_id}_v{self.current_version}.pkl"

    def select_client(self, all_clients) -> List[str]:
        return all_clients

    def compute_alpha(self, worker: Worker) -> float:
        return 1

    def aggregate(self, worker_manager: WorkerManager):
        # Get all workers that has the weight version with server
        completed_workers: dict[str, Worker] = worker_manager.get_completed_workers()
        self.current_version += 1

        sum_alpha = sum([completed_workers[w_id].alpha for w_id in completed_workers])

        alpha = {}
        for w_id in completed_workers:
            alpha[w_id] = self.compute_alpha(completed_workers[w_id]) / sum_alpha
            self.total_qod += completed_workers[w_id].qod.value
            self.global_model_update_data_size += completed_workers[w_id].batch_size
            self.avg_loss += completed_workers[w_id].loss / len(completed_workers)

        # Create a new weight with the same shape and type as a given weight.
        merged_weight = None
        for cli_id in completed_workers:
            weight_file = completed_workers[cli_id].get_weight_file_path()

            # Load the array from the specified file using the numpy.load function
            weight = self.get_model_weights(weight_file)

            if merged_weight is None:
                merged_weight = copy(weight)
            else:
                for layers in range(len(weight)):
                    merged_weight[layers] += 1 / len(completed_workers) * (
                            alpha[cli_id] / (self.current_version - completed_workers[cli_id].current_version)) * \
                                             weight[layers]

        # save weight file.
        save_location = Config.TMP_GLOBAL_MODEL_FOLDER + self.get_global_model_filename()
        print(save_location)
        print('='*20)
        with open(save_location, "wb") as f:
            pickle.dump(merged_weight, f)
        # print(merged_weight)

    def get_model_weights(self, file_path) -> ndarray:
        print("*"*10)
        print(file_path)
        print("*"*10)

        if os.path.isfile(file_path) is False:
            raise Exception("File not found")
        else:
            # return np.load(filepath, allow_pickle=True)
            with open(file_path, "rb") as f:
                weights = pickle.load(f)
            return weights
