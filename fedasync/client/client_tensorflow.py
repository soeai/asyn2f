from pika import BlockingConnection
from .client import Client
from model import ClientModel
import tensorflow as tf


class ClientTensorflow(ClientModel):

    def __init__(self, model, x_train, y_train, batch_size, x_test=None, y_test=None):
        self.new_weight = None
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
            if self.new_weight:
                self.__merge()
            else:
                pass
                # train as normal

    def evaluate(self):
        pass

    def data_preprocessing(self):
        pass

    def create_model(self):
        pass

    def __merge(self):
        pass
