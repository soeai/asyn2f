import logging
from datetime import datetime
from time import sleep
import numpy as np
import pickle
from asynfed.commons.conf import Config
from asynfed.commons.messages import ClientNotifyModelToServer

from ..client import Client
from ..ModelWrapper import ModelWrapper
from asynfed.commons.conf import Config

import os
LOGGER = logging.getLogger(__name__)

# This is the proposed federated asynchronous training algorithm of our paper
# More algorithms can be found at other files in this directory 
class ClientAsyncFl(Client):
    def __init__(self, model: ModelWrapper, role: str):
        super().__init__(role, model)
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
        self.model = model
        self._local_data_size = self.model.data_size
        self._local_qod = self.model.qod
        self._train_acc = 0.0
        self._train_loss = 0.0


    def train(self):
        # training nonstop until the server command to do so
        # or the client attempt to quit

        # before training, load the global model to set to be the client model weights 
        file_name = self._global_model_name.split('/')[-1]
        global_model_path = Config.TMP_GLOBAL_MODEL_FOLDER + file_name
        with open(global_model_path, "rb") as f:
            self.model.global_weights = pickle.load(f)
            
        # for tensorflow model, there is some conflict in the dimension of 
        # an initialized model and al already trained one
        # temporarily fixed this problem
        # by training the model before loading the global weights
        for images, labels in self.model.train_ds:
            self.model.fit(images, labels)
            break
        self.model.set_weights(self.model.global_weights)

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
            self._local_epoch += 1
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


            # Upload the weight to the storage (the remote server)
            remote_file_path = 'clients/' + str(self._client_id) + '/' + filename
            while True:
                if self._storage_connector.upload(save_location, remote_file_path) is True:
                    # After training, notify new model to the server.
                    message = ClientNotifyModelToServer(
                        client_id=self._client_id,
                        timestamp=datetime.now().timestamp(),
                        model_id=filename,
                        weight_file=remote_file_path,
                        # global_model_version_used=self._current_local_version,
                        global_model_version_used=self._global_model_version,
                        performance= self._train_acc,
                        loss_value= self._train_loss,
                    )

                    print("*" * 20)
                    print("Client Notify Model to Server")
                    print(message)
                    print("*" * 20)
                    self.notify_model_to_server(message.serialize())
                    LOGGER.info("ClientModel End Training, notify new model to server.")
                    self.update_profile()
                    break

            # break before completing the intended number of epoch
            # if the total training time excess some degree
            # set by client
            if self.model.delta_time:
                delta_time = datetime.now() - start_time
                delta_time_in_minute = delta_time.total_seconds() / 60
                if delta_time_in_minute >= self.model.delta_time:
                    break

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

