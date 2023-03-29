from typing import List

import numpy as np

from fedasync.commons.conf import Config
from fedasync.server.strategies import Strategy
import tensorflow


class AsyncFL(Strategy):
    def __init__(self):
        super().__init__()

    def get_global_model_filename(self):
        return f"{self.model_id}_v{self.current_version}.npy"

    def initialize_parameters(self):
        return self.get_model_weights()

    def select_client(self, all_clients) -> List[str]:
        return all_clients

    def aggregate(self, workers) -> None:
        print("Aggregate_______________________")
        pass

    def get_model_weights(self):
        file_path = f"{Config.TMP_MODEL_FOLDER}/{self.get_global_model_filename()}"
        return np.load(file_path, allow_pickle=True)
