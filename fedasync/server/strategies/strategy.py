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
    def get_global_model_filename(self):
        return f"{self.model_id}_v{self.current_version}"

    @abstractmethod
    def initialize_parameters(self):
        pass

    @abstractmethod
    def select_client(self, all_clients) -> List[str]:

        """ Implement the client selection logic by 
        """

    @abstractmethod
    def aggregate(self, workers) -> None:

        """Aggregate algorithm.
        """

    @abstractmethod
    def get_model_weights(self):
        """
        """
