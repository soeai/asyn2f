from pika import BlockingConnection
from .client import Client


class ClientTensorflow(Client):

    def __init__(self, queue_connection: BlockingConnection) -> None:
        super().__init__(queue_connection)

    # All methods below should be implement to work with 
    def set_weights(self, weights):
        pass

    def get_weights(self):
        pass

    def train(self):
        pass

    def evaluate(self):
        pass

    def data_preprocessing(self):
        pass

    def create_model(self):
        pass
