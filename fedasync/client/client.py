from abc import ABC, abstractmethod

from pika import BlockingConnection

from fedasync.client.client_queue_manager import ClientConsumer, ClientProducer
from fedasync.commons.utils.consumer import Consumer
from model import ClientModel
import json


class Client(ABC):
    """
    - This is the abstract Client class
    - Client can extend to use with Deep frameworks like tensorflow, pytorch by extending this abstract class and 
        implement it's abstract methods. 
    """
    def __init__(self):
        self._consumer: ClientConsumer = ClientConsumer()
        self._producer: ClientProducer = ClientProducer()

    def join_server(self) -> None:
        """
        - Implement the logic for client here.
        """
        pass

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

    @abstractmethod
    def data_preprocessing(self):
        pass

    @abstractmethod
    def create_model(self):
        pass


