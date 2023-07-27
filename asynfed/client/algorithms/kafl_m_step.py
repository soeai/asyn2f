import logging
import numpy as np
from threading import Lock

from time import sleep 

# from asynfed.client import Client



LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

lock = Lock()


# This is the proposed federated asynchronous training algorithm of our paper
# More algorithms can be found at other files in this directory 
class KaflMStep(object):

    # def __init__(self, client: Client):
    def __init__(self, client):
        self._client = client
        self._client.tracking_period = self._client.config.tracking_point


    def train(self):
        # for notifying global version used to server purpose
        self._client.training_process_info.global_version_used = self._client.global_model_info.version

        # for tensorflow model, there is some conflict in the dimension of 
        # an initialized model and al already trained one
        # fixed this problem
        # by training the model before loading the global weights
        current_global_model_file_name = self._client.global_model_info.get_file_name()
        file_exist, current_global_weights = self._client.load_weights_from_file(self._client.local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, 
                                                                          file_name= current_global_model_file_name)

        if file_exist:
            try:
                self._client.model.set_weights(current_global_weights)
            except Exception as e:
                LOGGER.info("=" * 20)
                LOGGER.info(e)
                LOGGER.info("=" * 20)
                self._client.get_model_dim_ready()
                self._client.model.set_weights(current_global_weights)

            # officially start the training process
            # quit after a number of epoch
            LOGGER.info("=" * 40)
            LOGGER.info("ClientModel Start Training")
            LOGGER.info("=" * 40)

            for _ in range(self._client.model.epoch):
                # record some info of the training process
                self._client.training_process_info.local_epoch += 1
                batch_num = 0
                # training per several epoch
                LOGGER.info(f"Enter epoch {self._client.training_process_info.local_epoch}")

                # reset loss and per after each epoch
                self._client.model.reset_train_loss()
                self._client.model.reset_train_performance()
                self._client.model.reset_test_loss()
                self._client.model.reset_test_performance()

                # if user require
                # Tracking the training process every x samples 
                # x define by user
                if self._client.tracking_period is not None:
                    self._client.tracking_point = self._client.tracking_period
                    self._client.multiplier = 1

                # training in each batch
                for images, labels in self._client.model.train_ds:
                    batch_num += 1
                    # training normally
                    self._client.training_process_info.train_acc, self._client.training_process_info.train_loss = self._client.model.fit(images, labels)

                    # Tracking the training process every x samples 
                    # x define by user as trakcing_period
                    if self._client.tracking_period is not None:
                        self._client.tracking_training_process(batch_num)


                # check for new global model every epoch
                if self._client.state.new_model_flag:
                    current_global_model_file_name = self._client.global_model_info.get_file_name()
                    file_exist, global_weights = self._client.load_weights_from_file(self._client.local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, 
                                                                                            current_global_model_file_name)
                    
                    if file_exist:
                        LOGGER.info(f"New model ? - {self._client.state.new_model_flag}")
                        LOGGER.info(f"Set global weight to the local model")    
                        self._client.model.set_weights(global_weights)

                    # if not file_exist, also changing the flag status
                    self._client.state.new_model_flag = False


                if self._client.model.test_ds:
                    for test_images, test_labels in self._client.model.test_ds:
                        test_acc, test_loss = self._client.model.evaluate(test_images, test_labels)
                else:
                    test_acc, test_loss = 0.0, 0.0


                LOGGER.info("*" * 20)
                LOGGER.info(
                    f'Epoch: {self._client.training_process_info.local_epoch}'
                    f'\tLast Batch Train Accuracy: {(self._client.training_process_info.train_acc * 100):.4f}, '
                    f'\tLast Batch Train Loss: {self._client.training_process_info.train_loss:.4f}, '
                    f'\tLast Batch Test Accuracy: {(test_acc * 100):.4f}, '
                    f'\tLast Batch Test Loss: {test_loss:.4f}'
                )
                LOGGER.info("*" * 20)

                # instead of notifying the server every epoch
                # reduce the communication by notifying every n epoch
                # n set by server as epoch_update_frequency param
                if self._client.training_process_info.local_epoch % self._client.server_training_config.epoch_update_frequency == 0:
                    min_acc = self._client.server_training_config.exchange_at.performance
                    min_epoch = self._client.server_training_config.exchange_at.epoch
                    if (min_acc <= self._client.training_process_info.train_acc) or (min_epoch <= self._client.training_process_info.local_epoch):
                        self._client.update_new_local_model_info()
                    else:
                        LOGGER.info("*" * 20)
                        LOGGER.info(f"At epoch {self._client.training_process_info.local_epoch}, current train acc is {self._client.training_process_info.train_acc:.4f}, which does not meet either the min acc {min_acc} or min epoch {min_epoch} to notify model to server")
                        LOGGER.info("*" * 20)

