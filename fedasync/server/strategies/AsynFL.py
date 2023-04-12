from copy import copy
from typing import List, Dict

import numpy as np
from numpy import ndarray
from tensorflow import Tensor
import tensorflow as tf

from fedasync.commons.conf import Config
from fedasync.server.objects import Worker
from fedasync.server.strategies import Strategy

from fedasync.server.worker_manager import WorkerManager


class AsynFL(Strategy):
    def __init__(self):
        super().__init__()
        self.alpha: Dict = {}

    def get_global_model_filename(self):
        return f"{self.model_id}_v{self.current_version}.npy"

    def select_client(self, all_clients) -> List[str]:
        return all_clients

    def aggregate(self, workers: dict[str, Worker], completed_workers: dict[str, Worker]) -> None:
        print("Aggregate_______________________")

        # Get all workers that has the weight version with server
        completed_workers: dict[str, Worker] = completed_workers
        self.current_version += 1

        sum_alpha = sum([completed_workers[w_id].alpha for w_id in completed_workers])
        alpha = {w_id: completed_workers[w_id].alpha / sum_alpha for w_id in completed_workers}

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
        np.save(Config.TMP_GLOBAL_MODEL_FOLDER + self.get_global_model_filename(), merged_weight)
        print(merged_weight)

    def get_model_weights(self, file_path) -> ndarray:
        return np.load(file_path, allow_pickle=True)
