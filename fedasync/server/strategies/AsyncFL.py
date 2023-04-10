from typing import List, Dict

import numpy as np
from numpy import ndarray
from tensorflow import Tensor
import tensorflow as tf

from fedasync.commons.conf import Config
from fedasync.server.objects import Worker
from fedasync.server.strategies import Strategy

from fedasync.server.worker_manager import WorkerManager


class AsyncFL(Strategy):
    def __init__(self):
        super().__init__()
        self.alpha: Dict = {}

    def calculate_beta(self):
        pass

    def get_global_model_filename(self):
        return f"{self.model_id}_v{self.current_version}.npy"

    def select_client(self, all_clients) -> List[str]:
        return all_clients

    def aggregate(self, workers: dict[str, Worker], completed_workers: dict[str, Worker]) -> None:
        print("Aggregate_______________________")
        total_weight: ndarray = None

        # Get all workers that has the weight version with server
        completed_workers: dict[str, Worker] = completed_workers
        self.current_version += 1
        beta = {}
        total_beta = 0

        if len(completed_workers) > 0:

            for w_id in completed_workers:
                total_beta += completed_workers[w_id].alpha

            for w_id in completed_workers:
                beta[w_id] = completed_workers[w_id].alpha / total_beta

            for cli_id in completed_workers:
                weight_file = completed_workers[cli_id].get_weight_file_path()

                # Load the array from the specified file using the numpy.load function
                weight = self.get_model_weights(weight_file)

                # if total weight is not set
                if total_weight is None:
                    total_weight = weight
                else:
                    for layers in range(len(weight)):
                        total_weight[layers] += 1 / len(completed_workers) * (
                                beta[cli_id] / (self.current_version - completed_workers[cli_id].current_version)) * \
                                        weight[layers]

        # save weight file.

    def get_model_weights(self, file_path) -> ndarray:
        return np.load(file_path, allow_pickle=True)
