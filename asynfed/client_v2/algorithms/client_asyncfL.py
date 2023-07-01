import logging
from datetime import datetime
from time import sleep
import numpy as np
import pickle
from asynfed.client_v2.messages.notify_model import NotifyModel
from asynfed.commons.conf import Config
from asynfed.commons.messages import ClientNotifyModelToServer

from asynfed.client_v2.client import Client
from asynfed.commons.messages.message_v2 import MessageV2
from asynfed.commons.utils.time_ultils import time_now
from ..ModelWrapper import ModelWrapper
from asynfed.commons.conf import Config
import tensorflow as tf

import os
LOGGER = logging.getLogger(__name__)


# This is the proposed federated asynchronous training algorithm of our paper
# More algorithms can be found at other files in this directory 
class ClientAsyncFl(Client):
    def __init__(self, model: ModelWrapper, config):
        super().__init__(config)
        '''
        - model must be an instance of an inheritant of class ModelWrapper
        - model.train_ds: require
        - model.test_ds: optional
        - train_ds and test_ds must in a format of a list of several batches
            each batch contain x, y
        - detail instruction (use as reference) of how to create a tensorflow model 
            is found at asynfed/client/tensorflow/tensorflow_framework
        - user is freely decided to follow the sample
            or create their own model in their own platform (pytorch,...)
        '''

        # print("*" * 20)
        # if tf.config.list_physical_devices('GPU'):
        #     tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[config["training_params"]['gpu_index']], 'GPU')
        #     print("Using GPU: ", tf.config.list_physical_devices('GPU')[config["training_params"]['gpu_index']])
        # else:
        #     print("Using CPU")
        # print("*" * 20)

        self.model = model
        self._local_data_size = self.model.data_size
        self._local_qod = self.model.qod
        self._train_acc = 0.0
        self._train_loss = 0.0

    def _get_model_dim_ready(self):
       for images, labels in self.model.train_ds:
            self.model.fit(images, labels)
            break
       
    def _load_weights_from_file(self, file_name, folder):
        full_path = folder + file_name
        # with open(full_path, "rb") as f:
        #     weights = pickle.load(f)
        print(full_path)
        print(os.getcwd())
        while not os.path.isfile(full_path):
            print("Sleep 5 second when the model is not ready, then retry")
            sleep(5)

        with open(full_path, "rb") as f:
            weights = pickle.load(f)
        return weights

    def train(self):
        # for tensorflow model, there is some conflict in the dimension of 
        # an initialized model and al already trained one
        # temporarily fixed this problem
        # by training the model before loading the global weights
        self._get_model_dim_ready()

        # check whether the client rejoin or training from the begining
        if self._local_epoch <= 1:
        # check whether there is more than one local model
        # if just 1 or 0, go with the global model
        # load the global model to set to be the client model weights 
            LOGGER.info("Load global model to be current local model")
            global_model_filename = self._global_model_name.split('/')[-1]
            self.model.global_weights = self._load_weights_from_file(global_model_filename, Config.TMP_GLOBAL_MODEL_FOLDER)
            self.model.set_weights(self.model.global_weights)
        
        # when client rejoin the training process
        else:
            print("*" * 20)
            LOGGER.info("Rejoin the training process")
            LOGGER.info("Loading the local weight...")
            # load current local weight
            current_local_model_filename = f'{self._client_id}_v{self._local_epoch}.pkl'
            current_local_weights = self._load_weights_from_file(current_local_model_filename, Config.TMP_LOCAL_MODEL_FOLDER)
            LOGGER.info("Loaded. ")
            print("*" * 20)
            self.model.set_weights(current_local_weights)

            # if the receive global model version is equal to the save global model version
            # just load the save current local version
            if self._save_global_model_version == self._current_global_version:
                LOGGER.info("The receive global model is equal to the save global model. Just load the current local weight and continue training")
            else:
                LOGGER.info("The receive global model is newer than the save one. Merging process needed.")
                # merge these weight
                previous_local_model_filename = f'{self._client_id}_v{self._local_epoch - 1}.pkl'
                previous_local_weights = self._load_weights_from_file(previous_local_model_filename, Config.TMP_LOCAL_MODEL_FOLDER)
                self.model.previous_weights = previous_local_weights
                self.model.current_weights = current_local_weights
                global_model_filename = self._global_model_name.split('/')[-1]
                self.model.global_weights = self._load_weights_from_file(global_model_filename, Config.TMP_GLOBAL_MODEL_FOLDER)
                self.__merge()


        LOGGER.info("*" * 40)
        LOGGER.info("ClientModel Start Training")
        LOGGER.info("*" * 40)
        # officially start the training process
        # while True:
        # quit after a number of epoch
        # or after a sufficient period of time
        from datetime import datetime
        start_time = datetime.now()
        for i in range(self.model.epoch):
            # since the current mnist model is small, set some sleeping time
            # to avoid overhead for the queue exchange and storage server
            LOGGER.info(f"Sleep for {Config.SLEEPING_TIME} seconds to avoid overhead")
            sleep(int(Config.SLEEPING_TIME))
            # record some info of the training process
            batch_num = 0
            # if user require
            # Tracking the training process every x samples 
            # x define by user
            batch_size = Config.BATCH_SIZE
            tracking_period = Config.TRACKING_POINT
            tracking_point = tracking_period

            multiplier = 1
            # reset loss and per after each epoch
            self.model.reset_train_loss()
            self.model.reset_train_performance()
            self.model.reset_test_loss()
            self.model.reset_test_performance()

            # training per several epoch
            LOGGER.info(f"Enter epoch {self._local_epoch}")
            for images, labels in self.model.train_ds:
                # Tracking the training process every x samples 
                # x define by user
                batch_num += 1
                total_trained_sample = batch_num * batch_size
                if total_trained_sample > tracking_point:
                    LOGGER.info(f"Training up to {total_trained_sample} samples")
                    multiplier += 1
                    tracking_point = tracking_period * multiplier

                # get the previous weights before the new training process within each batch
                self.model.previous_weights = self.model.get_weights()
                # training normally
                self._train_acc, self._train_loss = self.model.fit(images, labels)

                # merging when receiving a new global model
                if self._new_model_flag:
                    # before the merging process happens, need to retrieve current weights and global weights
                    # previous, current and global weights are used in the merged process
                    self.model.current_weights = self.model.get_weights()
                    # load global weights from file
                    global_model_path = Config.TMP_GLOBAL_MODEL_FOLDER + self._global_model_name
                    while not os.path.isfile(global_model_path):
                        print("*" * 20)
                        sleep(5)
                        print("Sleep 5 second when the model is not ready, then retry")
                        print("*" * 20)

                    with open(global_model_path, "rb") as f:
                        self.model.global_weights = pickle.load(f)
                    LOGGER.info(f"New model ? - {self._new_model_flag}")

                    # # print out the performance of the global model
                    # for test_images, test_labels in self.model.test_ds:
                    #     self._test_acc, self._test_loss = self.model.evaluate(test_images, test_labels)

                    LOGGER.info(
                        f"Merging process happens at epoch {self._local_epoch}, batch {batch_num} when receiving the global version {self._current_local_version}, current global version {self._previous_local_version}")
                    # merging
                    self.__merge()
                    # changing flag status
                    self._new_model_flag = False
                

            if self.model.test_ds:
                for test_images, test_labels in self.model.test_ds:
                    self._test_acc, self._test_loss = self.model.evaluate(test_images, test_labels)
            else:
                self._test_acc, self._test_loss = 0, 0

            

            LOGGER.info(
                f'Epoch: {self._local_epoch}'
                f'\tLast Batch Train Accuracy: {self._train_acc * 100}, '
                f'\tLast Batch Train Loss: {self._train_loss}, '
                f'\tLast Batch Test Accuracy: {self._test_acc * 100}'
                f'\tLast Batch Test Loss: {self._test_loss}, '
            )


            # Save weights locally after training
            filename = f'{self._client_id}_v{self._local_epoch}.pkl'
            save_location = Config.TMP_LOCAL_MODEL_FOLDER + filename
            with open(save_location, 'wb') as f:
                pickle.dump(self.model.get_weights(), f)
            # Print the weight location
            LOGGER.info(f'Saved weights to {save_location}')

            # Only when the local model is save, local epoch is updated
            self._local_epoch += 1

            # Upload the weight to the storage (the remote server)
            remote_file_path = 'clients/' + str(self._client_id) + '/' + filename
            while True:
                if self._storage_connector.upload(save_location, remote_file_path) is True:
                    # After training, notify new model to the server.
                    print('Notify new model to the server')
                    message = MessageV2(
                            headers={"timestamp": time_now(), "message_type": Config.CLIENT_NOTIFY_MESSAGE, "client_id": self._client_id, "session_id": self._session_id},
                            content=NotifyModel(remote_worker_weight_path=remote_file_path, 
                                                filename=filename,
                                                global_version_used=self._current_local_version, 
                                                loss=self._train_loss,
                                                performance= self._train_acc)).to_json()
                    self.queue_producer.send_data(message)
                    self.update_profile()
                    print('Notify new model to the server successfully')
                    break

            # break before completing the intended number of epoch
            # if the total training time excess some degree
            # set by client
            # if self.model.delta_time:
            #     delta_time = datetime.now() - start_time
            #     delta_time_in_minute = delta_time.total_seconds() / 60
            #     if delta_time_in_minute >= self.model.delta_time:
            #         break

    def __merge(self):
        LOGGER.info("MERGER weights.")
        # updating the value of each parameter of the local model
        # calculating the different to decide the formula of updating
        # calculation is performed on each corresponding layout
        # the different between the current weight and the previous weights

        # why if scenario? --> this situation is for tensorflow model when the dim of 
        # initialized model (fewer layers) and already trained model (more added layers)
        # is conflicted 
        if len(self.model.previous_weights) < len(self.model.current_weights):
            # applying when entering the training step with an initialized model (8 layers), 
            # not the pretrained one (18 layers)
            # in the 1st batch of the 1st epoch
            e_local = self.model.current_weights
        else:
            # perform calculation normally for all the other cases
            e_local = [layer_a - layer_b for layer_a, layer_b in zip(self.model.current_weights, self.model.previous_weights)]

        # e_local = [layer_a - layer_b for layer_a, layer_b in zip(self.model.current_weights, self.model.previous_weights)]

        # the different between the global weights and the current weights
        e_global = [layer_a - layer_b for layer_a, layer_b in zip(self.model.global_weights, self.model.current_weights)]
        # get the direction list (matrix)
        self.model.direction = [np.multiply(a, b) for a, b in zip(e_local, e_global)]

        # Calculate alpha variable to ready for the merging process
        # alpha depend on 
        # qod, loss and data size from both the server and the local client
        # qod
        local_qod = self._local_qod
        global_qod = self._global_avg_qod
        # data size
        local_size = self._local_data_size
        global_size = self._global_model_update_data_size
        # loss
        local_loss = self._train_loss
        global_loss = self._global_avg_loss
        # calculate alpha
        alpha = ( (local_qod*local_size) / (local_qod*local_size + global_qod*global_size) + local_loss/(local_loss + global_loss) )
        alpha = alpha / 2

        # create a blank array to store the result
        self.model.merged_weights = [np.zeros(layer.shape) for layer in self.model.current_weights]
        # base on the direction, global weights and current local weights
        # updating the value of each parameter to get the new local weights (from merging process)
        # set the index to move to the next layer
        i = 0
        for (local_layer, global_layer, direction_layer) in zip(self.model.current_weights, self.model.global_weights, self.model.direction):
            # access each element in each layer
            # np.where(condition, true, false)
            merged_layer = np.where(direction_layer >=0, global_layer, (1 - alpha) * global_layer + alpha * local_layer)
            self.model.merged_weights[i] = merged_layer
            i += 1

        # set the merged_weights to be the current weights of the model
        self.model.set_weights(self.model.merged_weights)

