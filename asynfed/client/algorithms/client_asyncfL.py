import logging
from datetime import datetime
from time import sleep
import numpy as np
import pickle
from asynfed.commons.conf import Config
from asynfed.commons.messages import ClientNotifyModelToServer

from ..client import Client
from ..ModelWrapper import ModelWrapper

LOGGER = logging.getLogger(__name__)

# This is the proposed federated asynchronous training algorithm of our paper
# More algorithms can be found at other files in this directory 
class ClientAsyncFl(Client):
    def __init__(self, model: ModelWrapper):
        super().__init__()
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
        self.local_data_size = self.model.data_size

    def train(self):
        # training nonstop until the server command to do so
        # or the client attempt to quit
        self._local_epoch = 0

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

        # officially start the training process
        while True:
            self._local_epoch += 1
            # for epoch in range(EPOCHS):
            LOGGER.info("*" * 40)
            LOGGER.info("ClientModel Start Training")
            LOGGER.info("*" * 40)
            # since the current mnist model is small, set some sleeping time
            # to avoid overhead for the queue exchange and storage server
            sleep(3)
            # record some info of the training process
            batch_num = 0

            # training per several epoch
            for images, labels in self.model.train_ds:
                batch_num += 1
                # get the previous weights before the new training process within each batch
                self.model.previous_weights = self.model.get_weights()
                # training normally
                train_acc, train_loss = self.model.fit(images, labels)

                # merging when receiving a new global model
                if self._new_model_flag:
                    # before the merging process happens, need to retrieve current weights and global weights
                    # previous, current and global weights are used in the merged process
                    self.model.current_weights = self.model.get_weights()
                    # load global weights from file
                    global_model_path = Config.TMP_GLOBAL_MODEL_FOLDER + self._global_model_name
                    with open(global_model_path, "rb") as f:
                        self.model.global_weights = pickle.load(f)
                    LOGGER.info(f"New model ? - {self._new_model_flag}")
                    LOGGER.info(
                        f"Merging process happens at epoch {self._local_epoch}, batch {batch_num} when receiving the global version {self._current_local_version}, current global version {self._previous_local_version}")
                    # merging
                    self.__merge()
                    # changing flag status
                    self._new_model_flag = False

                if self.model.test_ds:
                    for test_images, test_labels in self.model.test_ds:
                        test_acc, test_loss = self.model.evaluate(test_images, test_labels)

            # if there is a test dataset 
            # --> send acc and loss of test dataset
            if self.model.test_ds:
                acc = test_acc
                loss = test_loss
            else:
                acc = train_acc
                loss = train_loss
                test_acc = 0
                test_loss = None

            LOGGER.info(
                f'Epoch: {self._local_epoch}'
                f'\tLast Batch Train Accuracy: {train_acc * 100}, '
                f'\tLast Batch Train Loss: {train_loss}, '
                f'\tLast Batch Test Accuracy: {test_acc * 100}'
                f'\tLast Batch Test Loss: {test_loss}, '
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
                        model_id=filename,
                        global_model_version_used=self._current_local_version,
                        timestamp=datetime.now().timestamp(),
                        weight_file=remote_file_path,
                        performance=acc,
                        loss_value=loss,
                    )
                    self.notify_model_to_server(message.serialize())
                    LOGGER.info("ClientModel End Training, notify new model to server.")
                    self.update_profile()
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

        # calculate alpha variable to ready for the merging process
        # alpha depend on qod, loss and sum of datasize from the server
        # now, just calculate alpha based on the size (local dataset size / local dataset size + server dataset size)
        alpha = (self.local_data_size) / (self.local_data_size + self._global_model_update_data_size)

        # create a blank array to store the result
        self.model.merged_weights = [np.zeros(layer.shape) for layer in self.model.current_weights]
        # base on the direction, global weights and current local weights
        # updating the value of each parameter to get the new local weights (from merging process)
        # set the index to move to the next layer
        # i = 0
        for (local_layer, global_layer, direction_layer) in zip(self.model.current_weights, self.model.global_weights, self.model.direction):
            # access each element in each layer
            # np.where(condition, true, false)
            merged_layer = np.where(direction_layer >=0, global_layer, (1 - alpha) * global_layer + alpha * local_layer)
            self.model.merged_weights[i] = merged_layer
            i += 1

        # set the merged_weights to be the current weights of the model
        self.model.set_weights(self.model.merged_weights)

