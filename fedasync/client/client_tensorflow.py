import logging
import tensorflow as tf
from .client import Client

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class ClientTensorflow(Client):

    def __init__(self, model, x_train, y_train, batch_size, x_test=None, y_test=None):
        super().__init__()
        self.model = model

        # variables
        self.new_weight = None
        self.x_train = x_train
        self.y_train = y_train
        self.x_test = x_test
        self.y_test = y_test
        self.batch_size = batch_size

    def set_weights(self, weights):
        pass

    def get_weights(self):
        pass

    def train(self):

        LOGGER.info("ClientModel Start Training")

        for b in range(self.batch_size):
            if self.__new_model_flag:
                LOGGER.info(f"New model ? - {self.__new_model_flag}")
                self.__merge()
                self.__new_model_flag = False
            else:
                LOGGER.info("training as normal")
                pass

                # train as normal

    def evaluate(self):
        pass

    def __merge(self):
        LOGGER.info("MERGER weights.")
        pass
