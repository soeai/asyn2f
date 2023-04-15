import logging
from datetime import datetime
from time import sleep

import numpy as np

from .client import Client
from ..commons.conf import Config
from ..commons.messages.client_notify_model_to_server import ClientNotifyModelToServer

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
        self.model.set_weights(weights)

    def get_weights(self):
        self.model.get_weights()

    def train(self):
        while True:
            LOGGER.info("ClientModel Start Training")
            n_iter = int(self.x_train.shape[0] / self.batch_size)

            for b in range(n_iter):
                sleep(3)
                if self._new_model_flag:
                    print('New model received. Start merging...')
                    self.__merge()
                    self._new_model_flag = False
                    # If there are no merging flag, train as normal.
                loss = 0
                print(f'batch {b + 1}/{n_iter} -- loss: {loss}')

            # Save weights after training
            # filename = self.client_id + "_" + str(self.local_version) + ".npy"
            filename = 'weights.npy'
            save_location = Config.TMP_LOCAL_MODEL_FOLDER + filename
            # np.save(save_location, self.model.get_weights())
            # Print the weight location
            print(f'Saved weights to {save_location}')

            # Upload the weight to the storage
            self.storage_connector.upload(self.client_id, save_location)

            # After training, notify new model to the server.
            message = ClientNotifyModelToServer(
                client_id=self.client_id,
                model_id=self.local_version,
                global_model_version_used=self.local_version,
                timestamp=datetime.now().timestamp(),
                loss_value=self.evaluate(),
                weight_file=filename,
                performance=0.0,
            )
            self.notify_model_to_server(message.serialize())
            LOGGER.info("ClientModel End Training, notify new model to server.")

    def evaluate(self):
        loss = 0
        return loss

    def __merge(self):
        LOGGER.info("MERGER weights.")
        pass
