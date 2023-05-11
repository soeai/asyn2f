import logging
import os
from datetime import datetime
from time import sleep

import numpy as np
import pickle

# from tensorflow_examples.mnist.lenet_model import LeNet
from fedasync.client.tensorflow_examples.mnist.lenet_model import LeNet
from .client import Client
from ..commons.conf import ClientConfig
from ..commons.messages.client_notify_model_to_server import ClientNotifyModelToServer

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class ClientTensorflow(Client):

    # def __init__(self, model, x_train, y_train, batch_size, x_test=None, y_test=None):
    def __init__(self, model: LeNet, local_data_size: int, train_ds, test_ds, evaluate_ds=None):
        super().__init__()
        # model must be create from Model module of tensorflow
        # from tensorflow.keras import Model
        self.model = model
        self.local_data_size = local_data_size

        # these dataset is in the format
        # tensorflow.python.data.ops.batch_op._BatchDataset
        self.train_ds = train_ds
        self.test_ds = test_ds
        self.evaluate_ds = evaluate_ds

        # batch size is defined in data preprocessing module
        # variables generated in training process in the model, especially used for merging
        # # loss
        # self.loss_object = None
        # # optimizer
        # self.optimizer = None
        # # metric
        # self.train_loss = None
        # self.train_accuracy = None
        # self.test_loss = None
        # self.test_accuracy = None

        # # variable for training process
        # self.previous_weights = None
        # self.current_weights = None
        # self.global_weights = None
        # self.direction = None
        # self.merged_result = None

    def set_weights(self, weights):
        self.model.set_weights(weights)

    def get_weights(self):
        self.model.get_weights()

    # def train(self, EPOCHS = 10):
    def train(self):
        # training nonstop until the server command to do so
        # or the client attempt to quit
        self.local_epoch = 0
        while True:
            self.local_epoch += 1
            # for epoch in range(EPOCHS):
            LOGGER.info("ClientModel Start Training")
            batch_num = 0

            sleep(3)

            for images, labels in self.train_ds:
                batch_num += 1
                # Reset the metrics at the start of the next epoch
                self.model.train_loss.reset_states()
                self.model.train_accuracy.reset_states()
                self.model.test_loss.reset_states()
                self.model.test_accuracy.reset_states()

                # get the previous weights before the new training process within each batch
                self.model.previous_weights = self.model.get_weights()
                # training normally
                self.model.train_step(images, labels)

                # merging when receiving a new global model
                if self._new_model_flag:
                    # before the merging process happens, need to retrieve current weights and global weights
                    # previous, current and global weights are used in the merged process
                    self.model.current_weights = self.model.get_weights()
                    # load global weights from file
                    global_model_path = ClientConfig.TMP_GLOBAL_MODEL_FOLDER + self.global_model_name

                    print("0" * 20)
                    print(global_model_path)
                    print("0" * 20)

                    with open(global_model_path, "rb") as f:
                        self.model.global_weights = pickle.load(f)

                    print("0" * 20)
                    print(self.model.global_weights)
                    print("0" * 20)


                    LOGGER.info(f"New model ? - {self._new_model_flag}")
                    LOGGER.info(
                        f"Merging process happens at epoch {self.local_epoch}, batch {batch_num} when receiving the global version {self.current_local_version}, current global version {self.previous_local_version}")

                    self.__merge()
                    self.model.merged_weights = self.model.get_weights()
                    self._new_model_flag = False

            if self.test_ds:
                for test_images, test_labels in self.test_ds:
                    self.model.test_step(test_images, test_labels)

            LOGGER.info(
                f'Epoch {self.local_epoch}, '
                f'Loss: {self.model.train_loss.result()}, '
                f'Accuracy: {self.model.train_accuracy.result() * 100}, '
                f'Test Loss: {self.model.test_loss.result()}, '
                f'Test Accuracy: {self.model.test_accuracy.result() * 100}'
            )

            # Save weights after training
            # filename = self.client_id + "_" + str(self.current_local_version) + ".pkl"
            # save weights to local location in pickle format
            filename = f'{self.client_id}_{self.local_epoch}.pkl'
            save_location = ClientConfig.TMP_LOCAL_MODEL_FOLDER + filename
            remote_file_path = self.access_key_id + '/' + filename
            with open(save_location, 'wb') as f:
                pickle.dump(self.model.get_weights(), f)
            # Print the weight location
            print(f'Saved weights to {save_location}')

            # Upload the weight to the storage
            while True:
                if self.storage_connector.upload(save_location, remote_file_path, 'fedasyn') is True:
                    # After training, notify new model to the server.
                    message = ClientNotifyModelToServer(
                        client_id=self.client_id,
                        model_id=filename,
                        global_model_version_used=self.current_local_version,
                        timestamp=datetime.now().timestamp(),
                        loss_value=self.evaluate(self.test_ds)['loss'],
                        weight_file=remote_file_path,
                        performance=0.0,
                    )
                    self.notify_model_to_server(message.serialize())
                    LOGGER.info("ClientModel End Training, notify new model to server.")
                    break

    def evaluate(self, test_ds):
        # test_ds: tensorflow.python.data.ops.batch_op._BatchDataset
        self.model.test_loss.reset_states()
        self.model.test_accuracy.reset_states()
        for test_images, test_labels in test_ds:
            self.model.test_step(test_images, test_labels)
        result = {"acc": float(self.model.test_accuracy.result()), "loss": float(self.model.test_loss.result())}
        return result

    def __merge(self):
        LOGGER.info("MERGER weights.")
        # updating the value in each parameters of the local model
        # calculate the different to decide the formula of updating
        # the calculation is performed on each corresponding layout
        # the different between the current weight and the previous weights
        if len(self.model.previous_weights) < len(self.model.current_weights):
            # applying when entering the training step with an initialized model (8 layers), not the pretrained one (18 layers)
            # in the 1st batch of the 1st epoch
            e_local = self.model.current_weights
        else:
            # perform calculation normally for all the other cases
            e_local = [layer_a - layer_b for layer_a, layer_b in
                       zip(self.model.current_weights, self.model.previous_weights)]

        # the different between the global weights and the current weights
        e_global = [layer_a - layer_b for layer_a, layer_b in
                    zip(self.model.global_weights, self.model.current_weights)]

        # check the dimension of these variables to see whether it fits one another
        # print(f"total layers of previous weights: {len(self.model.previous_weights)}, total layers of current weights: {len(self.model.current_weights)}")
        # print(f"total layers of e_local: {len(e_local)}, total layers of e_global: {len(e_global)}")
        # get the direction list (matrix)
        self.model.direction = [np.multiply(a, b) for a, b in zip(e_local, e_global)]
        # print(f"total layers of direction: {len(self.model.direction)}")

        # calculate alpha variable to ready for the merging process
        # alpha depend on qod, loss and sum of datasize from the server
        # now, just calculate alpha based on the size (local dataset size / local dataset size + server dataset size)
        alpha = (self.local_data_size) / (self.local_data_size + self.global_model_update_data_size)

        # create a blank array to store the result
        self.model.merged_result = [np.zeros(layer.shape) for layer in self.model.current_weights]
        # base on the direction, global weights and current local weights
        # updating the value of each parameter to get the new local weights (from merging process)
        # set the index to move to the next layer
        t = 0
        # # check some param of the merging process
        # self.model.total = 0
        # self.model.different_direction = 0
        # self.model.same_direction = 0
        # access each layer of these variables correspondingly 
        for (local_layer, global_layer, direction_layer) in zip(self.model.current_weights, self.model.global_weights,
                                                                self.model.direction):
            # print(local_layer.shape, global_layer.shape, direction_layer.shape)
            # access each element in each layer
            it = np.nditer([local_layer, global_layer, direction_layer], flags=['multi_index'])
            for local_element, global_element, direction_element in it:
                # self.model.total += 1
                index = it.multi_index

                if direction_element >= 0:
                    result_element = global_element
                    # self.model.different_direction += 1
                else:
                    result_element = (1 - alpha) * global_element + alpha * local_element
                    # self.model.same_direction += 1

                self.model.merged_result[t][index] = result_element
            # move to the next layer
            t += 1
            # set the current weights of the model to be the result of the merging process
        self.model.set_weights(self.model.merged_result)
