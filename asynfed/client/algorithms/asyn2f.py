import os
import logging
from typing import List
import numpy as np
import pickle
from threading import Lock

from time import sleep 

from asynfed.common.messages import ExchangeMessage
import asynfed.common.messages as message_utils 
from asynfed.common.messages.server import ServerModelUpdate
from asynfed.common.messages.server.server_response_to_init import ServerRespondToInit, StorageInfo

from asynfed.common.config import MessageType


from asynfed.common.messages.client import ClientModelUpdate, NotifyEvaluation, TesterRequestStop

from asynfed.client import Client



LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

lock = Lock()


# This is the proposed federated asynchronous training algorithm of our paper
# More algorithms can be found at other files in this directory 
class Asyn2fClient(Client):
    '''
    - model must be an instance of an inheritant of class ModelWrapper
    - for train
        - model.train_ds: require 
        - model.test_ds: optional
    - for tester: test_ds is required

    - train_ds and test_ds must in a format of a list of several batches
        each batch contain x, y
    - detail instruction (use as reference) of how to create a tensorflow model 
        is found at asynfed/client/tensorflow/tensorflow_framework
    - user is freely decided to follow the sample
        or create their own model in their own platform (pytorch,...)
    '''
    def __init__(self, model, config: dict):
        super().__init__(model, config)


    def _train(self):
        self._tracking_period = self._config.tracking_point
        
        # for notifying global version used to server purpose
        self._training_process_info.global_version_used = self._global_model_info.version

        # for tensorflow model, there is some conflict in the dimension of 
        # an initialized model and al already trained one
        # fixed this problem
        # by training the model before loading the global weights
        current_global_model_file_name = self._global_model_info.get_file_name()
        file_exist, current_global_weights = self._load_weights_from_file(self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, 
                                                                          file_name= current_global_model_file_name)

        if file_exist:
            try:
                self._model.set_weights(current_global_weights)
            except Exception as e:
                LOGGER.info("=" * 20)
                LOGGER.info(e)
                LOGGER.info("=" * 20)
                self._get_model_dim_ready()
                self._model.set_weights(current_global_weights)

            # officially start the training process
            # quit after a number of epoch
            LOGGER.info("=" * 40)
            LOGGER.info("ClientModel Start Training")
            LOGGER.info("=" * 40)

            for _ in range(self._model.epoch):
                # record some info of the training process
                self._training_process_info.local_epoch += 1
                batch_num = 0
                # training per several epoch
                LOGGER.info(f"Enter epoch {self._training_process_info.local_epoch}")

                # reset loss and per after each epoch
                self._model.reset_train_loss()
                self._model.reset_train_performance()
                self._model.reset_test_loss()
                self._model.reset_test_performance()

                # if user require
                # Tracking the training process every x samples 
                # x define by user
                if self._tracking_period is not None:
                    self._tracking_point = self._tracking_period
                    self._multiplier = 1

                # training in each batch
                for images, labels in self._model.train_ds:
                    batch_num += 1
                    # get the previous weights before the new training process within each batch
                    self._model.previous_weights = self._model.get_weights()
                    # training normally
                    self._training_process_info.train_acc, self._training_process_info.train_loss = self._model.fit(images, labels)

                    # Tracking the training process every x samples 
                    # x define by user as trakcing_period
                    if self._tracking_period is not None:
                        self._tracking_training_process(batch_num)

                    # merging when receiving a new global model
                    if self._state.new_model_flag:
                        # update some tracking info
                        self._training_process_info.previous_global_version_used = self._training_process_info.global_version_used
                        self._training_process_info.global_version_used = self._global_model_info.version

                        # before the merging process happens, need to retrieve current weights and global weights
                        # previous, current and global weights are used in the merged process
                        self._model.current_weights = self._model.get_weights()
                        # load global weights from file
                        current_global_model_file_name = self._global_model_info.get_file_name()
                        file_exist, self._model.global_weights = self._load_weights_from_file(self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, 
                                                                                              current_global_model_file_name)
                        
                        
                        if file_exist:
                            LOGGER.info(f"New model ? - {self._state.new_model_flag}")
                            LOGGER.info(
                                f"Merging process happens at epoch {self._training_process_info.local_epoch}, batch {batch_num} when receiving the global version {self._training_process_info.global_version_used}, current global version {self._training_process_info.previous_global_version_used}")
                                
                            # changing flag status
                            self._state.new_model_flag = False
                            # merging
                            self._merge()
                        else:
                            pass
                            # LOGGER.info(f"Cannot find the file in the directory: {}")

                        # if not file_exist, also changing the flag status
                        self._state.new_model_flag = False


                if self._model.test_ds:
                    for test_images, test_labels in self._model.test_ds:
                        self._test_acc, self._test_loss = self._model.evaluate(test_images, test_labels)
                else:
                    self._test_acc, self._test_loss = 0.0, 0.0


                LOGGER.info("*" * 20)
                LOGGER.info(
                    f'Epoch: {self._training_process_info.local_epoch}'
                    f'\tLast Batch Train Accuracy: {(self._training_process_info.train_acc * 100):.4f}, '
                    f'\tLast Batch Train Loss: {self._training_process_info.train_loss:.4f}, '
                    f'\tLast Batch Test Accuracy: {(self._test_acc * 100):.4f}, '
                    f'\tLast Batch Test Loss: {self._test_loss:.4f}'
                )
                LOGGER.info("*" * 20)
                min_acc = self._server_training_config.exchange_at.performance
                min_epoch = self._server_training_config.exchange_at.epoch
                if (min_acc <= self._training_process_info.train_acc) or (min_epoch <= self._training_process_info.local_epoch):
                    self._update_new_local_model_info()

                else:
                    LOGGER.info("*" * 20)
                    LOGGER.info(f"At epoch {self._training_process_info.local_epoch}, current train acc is {self._training_process_info.train_acc:.4f}, which does not meet either the min acc {min_acc} or min epoch {min_epoch} to notify model to server")
                    LOGGER.info("*" * 20)



    def _merge(self):
        LOGGER.info("MERGER weights.")
        # updating the value of each parameter of the local model
        # calculating the different to decide the formula of updating
        # calculation is performed on each corresponding layout
        # the different between the current weight and the previous weights
        e_local = [layer_a - layer_b for layer_a, layer_b in zip(self._model.current_weights, self._model.previous_weights)]

        # the different between the global weights and the current weights
        e_global = [layer_a - layer_b for layer_a, layer_b in zip(self._model.global_weights, self._model.current_weights)]

        # get the direction list (matrix)
        self._model.direction = [np.multiply(a, b) for a, b in zip(e_local, e_global)]

        # Calculate alpha variable to ready for the merging process
        # alpha depend on 
        # qod, loss and data size from both the server and the local client
        # qod
        # local_qod = self._local_qod
        local_qod = self._config.dataset.qod
        global_qod = self._global_model_info.avg_qod
        # data size
        local_size = self._config.dataset.data_size
        global_size = self._global_model_info.total_data_size
        # loss
        local_loss = self._training_process_info.train_loss
        global_loss = self._global_model_info.avg_loss
        # calculate alpha
        data_depend = (1 - self._config.training_params.beta) * (local_qod * local_size) / (local_qod * local_size + global_qod * global_size)
        loss_depend = self._config.training_params.beta * global_loss / (local_loss + global_loss)
        alpha = data_depend + loss_depend

        LOGGER.info("-" * 20)
        LOGGER.info(f"local loss: {local_loss}")
        LOGGER.info(f"global loss: {global_loss}")
        LOGGER.info(f"local size: {local_size}")
        LOGGER.info(f"global data size: {global_size}")
        LOGGER.info(f"alpha = {alpha}")
        LOGGER.info("-" * 20)

        # create a blank array to store the result
        self._model.merged_weights = [np.zeros(layer.shape, dtype=np.float32) for layer in self._model.current_weights]
        # base on the direction, global weights and current local weights
        # updating the value of each parameter to get the new local weights (from merging process)
        for i, (local_layer, global_layer, direction_layer) in enumerate(zip(self._model.current_weights, self._model.global_weights, self._model.direction)):
            # access each element in each layer
            # np.where(condition, true, false)
            self._model.merged_weights[i] = np.where(direction_layer > 0, global_layer, (1 - alpha) * global_layer + alpha * local_layer)


        # set the merged_weights to be the current weights of the model
        self._model.set_weights(self._model.merged_weights)
            


