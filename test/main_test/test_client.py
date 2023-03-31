from fedasync.client.queue_manager import ClientQueueConnector
from fedasync.client.client_tensorflow import ClientTensorflow


class MyClient(ClientQueueConnector):
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


tf_client = ClientTensorflow()
client = MyClient()
client.run()
