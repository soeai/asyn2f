from client import ClientModel


class ClientTensorflow(ClientModel):

    def __init__(self, model, x_train, y_train, batch_size, x_test=None, y_test=None):
        self.model = model
        self.x_train = x_train
        self.y_train = y_train
        self.x_test = x_test
        self.y_test = y_test
        self.batch_size = batch_size

    def set_weights(self, weights):
        pass

    def get_weights(self):
        pass

    def train_step(self, return_gradient=False):
        pass

    def evaluate(self):
        pass