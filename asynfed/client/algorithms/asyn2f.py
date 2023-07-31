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
class Asyn2f(object):

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
                    # get the previous weights before the new training process within each batch
                    self._client.model.previous_weights = self._client.model.get_weights()
                    # training normally
                    self._client.training_process_info.train_acc, self._client.training_process_info.train_loss = self._client.model.fit(images, labels)

                    # Tracking the training process every x samples 
                    # x define by user as trakcing_period
                    if self._client.tracking_period is not None:
                        self._client.tracking_training_process(batch_num)

                    # merging when receiving a new global model
                    if self._client.state.new_model_flag:
                        

                        # before the merging process happens, need to retrieve current weights and global weights
                        # previous, current and global weights are used in the merged process
                        self._client.model.current_weights = self._client.model.get_weights()
                        # load global weights from file
                        current_global_model_file_name = self._client.global_model_info.get_file_name()
                        file_exist, self._client.model.global_weights = self._client.load_weights_from_file(self._client.local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, 
                                                                                              current_global_model_file_name)
                        
                        
                        if file_exist:
                            LOGGER.info(f"New model ? - {self._client.state.new_model_flag}")
                            # update some tracking info
                            self._client.training_process_info.previous_global_version_used = self._client.training_process_info.global_version_used
                            self._client.training_process_info.global_version_used = self._client.global_model_info.version
                            LOGGER.info(
                        f"Merging process happens at epoch {self._client.training_process_info.local_epoch}, batch {batch_num} when receiving the global version {self._client.training_process_info.global_version_used}, current global version {self._client.training_process_info.previous_global_version_used}")
                                
                            # changing flag status
                            self._client.state.new_model_flag = False
                            # merging
                            self._merge()
                        else:
                            pass
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


    def _merge(self):
        LOGGER.info("MERGER weights.")
        # updating the value of each parameter of the local model
        # calculating the different to decide the formula of updating
        # calculation is performed on each corresponding layout
        # the different between the current weight and the previous weights
        e_local = [layer_a - layer_b for layer_a, layer_b in zip(self._client.model.current_weights, self._client.model.previous_weights)]

        # the different between the global weights and the current weights
        e_global = [layer_a - layer_b for layer_a, layer_b in zip(self._client.model.global_weights, self._client.model.current_weights)]

        # get the direction list (matrix)
        self._client.model.direction = [np.multiply(a, b) for a, b in zip(e_local, e_global)]

        # Calculate alpha variable to ready for the merging process
        # alpha depend on 
        # qod, loss and data size from both the server and the local client
        # qod
        local_qod = self._client.config.dataset.qod
        global_qod = self._client.global_model_info.avg_qod
        # data size
        local_size = self._client.config.dataset.data_size
        global_size = self._client.global_model_info.total_data_size
        # loss
        local_loss = self._client.training_process_info.train_loss
        global_loss = self._client.global_model_info.avg_loss
        # calculate alpha
        data_depend = (1 - self._client.config.training_params.beta) * (local_qod * local_size) / (local_qod * local_size + global_qod * global_size)
        loss_depend = self._client.config.training_params.beta * global_loss / (local_loss + global_loss)
        alpha = data_depend + loss_depend

        LOGGER.info("-" * 20)
        LOGGER.info(f"local loss: {local_loss}")
        LOGGER.info(f"global loss: {global_loss}")
        LOGGER.info(f"local size: {local_size}")
        LOGGER.info(f"global data size: {global_size}")
        LOGGER.info(f"alpha = {alpha}")
        LOGGER.info("-" * 20)

        # create a blank array to store the result
        self._client.model.merged_weights = [np.zeros(layer.shape, dtype=np.float32) for layer in self._client.model.current_weights]
        # base on the direction, global weights and current local weights
        # updating the value of each parameter to get the new local weights (from merging process)
        for i, (local_layer, global_layer, direction_layer) in enumerate(zip(self._client.model.current_weights, self._client.model.global_weights, self._client.model.direction)):
            # access each element in each layer
            # np.where(condition, true, false)
            self._client.model.merged_weights[i] = np.where(direction_layer > 0, global_layer, (1 - alpha) * global_layer + alpha * local_layer)


        # set the merged_weights to be the current weights of the model
        self._client.model.set_weights(self._client.model.merged_weights)
            


