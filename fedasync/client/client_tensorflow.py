from model import ClientModel
import tensorflow as tf


class ClientTensorflow(ClientModel):

    def __init__(self, model, x_train, y_train, batch_size, x_test=None, y_test=None):
        self.model = model
        self.x_train = x_train
        self.y_train = y_train
        self.x_test = x_test
        self.y_test = y_test
        self.batch_size = batch_size
        self.__flag = False

    def set_weights(self, weights):
        self.new_weight = weights
        self.__flag = True

    def get_weights(self):
        pass

    def train(self):
        for b in range(self.batch_size):
            if self.__flag:
                self.__merge()
                self.__flag = False
            else:
                pass
                # train as normal

    def evaluate(self):
        pass

    def __merge(self):
        pass