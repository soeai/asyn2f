from fedasync.client.client import Client
from fedasync.client.client_tensorflow import ClientTensorflow


class MyClient(Client):
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


tf_client = ClientTensorflow(None, None, None, None)
tf_client.run_queue()
