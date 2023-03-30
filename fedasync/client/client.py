import threading
from abc import ABC, abstractmethod
from pika import BlockingConnection
from fedasync.client.client_queue_manager import ClientConsumer, ClientProducer
from fedasync.client.client_storage_connector import ClientStorage
from fedasync.commons.messages.client_init_connect_to_server import ClientInit
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
        self.storage_connector = None
        self.local_version = 0

    def run(self) -> None:
        # Create 1 thread to listen on the queue.
        consuming_thread = threading.Thread(target=self._consumer.run,
                                            name="fedasync_client_consuming_thread")
        consuming_thread.start()

        # Send a message to server to init connection
        message = ClientInit()
        self._producer.init_connect_to_server(
            message.serialize()
        )
        while not self._consumer.storage_access_key and not self._consumer.storage_secret_key:
            continue
        storage_access_key, storage_secret_key = self._consumer.storage_access_key, self._consumer.storage_secret_key
        self.storage_connector = ClientStorage(storage_access_key, storage_secret_key, storage_access_key)

        if self._consumer.global_model_version and self.is_new_global_model(self._consumer.global_model_version):
            self.storage_connector.get_model(self._consumer.global_model_version)
            self.local_version = self._consumer.global_model_version

    def is_new_global_model(self, global_model_version: str) -> bool:
        '''
        Check if the global model version is newer than the local model version
        Parameters
        ----------
        global_model_version

        Returns
        -------
        '''

        # return self.local_version > self._consumer.global_model_version()
        return True

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


