from typing import List, Dict
from abc import ABC, abstractmethod
from fedasync.server.objects.worker import Worker


class Strategy(ABC):
    """
    This here the Interface of strategy, follow the strategy design pattern.
    Any new strategy will follow this interface. 
    """

    def __init__(self):
        self.current_version = 0
        self.model_id = 0
        self.avg_loss = 0.0
        self.global_model_update_data_size = 0

    @abstractmethod
    def initialize_parameters(self):
        pass

    @abstractmethod
    def select_client(self, all_clients) -> List[str]:

        """ Implement the client selection logic by 
        """

    @abstractmethod
    def aggregate(self, weights) -> None:

        """Aggregate algorithm.
        """

    @abstractmethod
    def get_model_weights(self):
        """
        """

    @abstractmethod
    def set_model_weights(self, weights):
        pass

    @abstractmethod
    def data_preprocessing(self):
        pass
