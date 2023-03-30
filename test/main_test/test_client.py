from fedasync.client.client import Client

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

client = MyClient()
client.run()