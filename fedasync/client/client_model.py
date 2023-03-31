import threading
from abc import ABC, abstractmethod

from fedasync.client.client_storage_connector import ClientStorage
from fedasync.client.queue_manager import ClientQueueConnector


class ClientModel(ABC):

    def __init__(self, model):
        # Dependencies
        self._storage_connector: ClientStorage = None
        self.queue_connector = ClientQueueConnector(self)

        self.model = model
        self.global_model_update_data_size = 0
        self.global_avg_loss = 0.0
        self.global_model_name = None
        self.global_model_version = 0
        self.local_version = 0
        self.__new_model_flag = False

    def run(self):
        self.queue_connector.run()

    # Abstract methods
    @abstractmethod
    def set_weights(self, weights):
        pass

    @abstractmethod
    def get_weights(self):
        pass

    @abstractmethod
    def train(self):
        pass

    @abstractmethod
    def evaluate(self):
        pass
