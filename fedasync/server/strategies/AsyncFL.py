from typing import List

from fedasync.server.strategies import Strategy


class AsyncFL(Strategy):
    def initialize_parameters(self):
        pass

    def select_client(self, all_clients) -> List[str]:
        pass

    def aggregate(self, weights) -> None:
        pass

    def get_model_weights(self):
        pass

    def set_model_weights(self, weights):
        pass

    def __init__(self):
        super().__init__()


