import os
import logging
from datetime import datetime
from time import sleep
import numpy as np
from tqdm import tqdm
import pickle

from asynfed.client.messages import NotifyEvaluation
from asynfed.client.messages import NotifyModel
from asynfed.client.messages.require_stop import RequireStop
from asynfed.commons import Config
from asynfed.client import Client

from asynfed.commons.messages import MessageV2
from asynfed.commons.utils import time_now
from asynfed.commons import Config

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


# This is the proposed federated asynchronous training algorithm of our paper
# More algorithms can be found at other files in this directory 
class ClientAsyncFl(Client):
    def __init__(self, model, config: dict, save_log=False):
        super().__init__(model, config, save_log)
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

        if self._role == "train":
            self._batch_size = config['training_params']['batch_size']
            self._beta = config['training_params']['beta']
            self._tracking_period = config.get('others', {}).get('tracking_point', None)

        elif self._role == "test":
            # using config or set default value
            self._expected_performance: float = config.get('stop_conditions', {}).get('expected_performance', 0.95)
            self._expected_loss: float = config.get('stop_conditions', {}).get('expected_loss', 0.02)

    def train(self):
        # for tensorflow model, there is some conflict in the dimension of 
        # an initialized model and al already trained one
        # fixed this problem
        # by training the model before loading the global weights
        current_global_weights = self._load_weights_from_file(self._global_model_name, Config.TMP_GLOBAL_MODEL_FOLDER)
        # for notifying global version used to server purpose
        self._merged_global_version = self._current_global_version
        try:
            self.model.set_weights(current_global_weights)
        except Exception as e:
            LOGGER.info("=" * 20)
            LOGGER.info(e)
            LOGGER.info("=" * 20)
            self._get_model_dim_ready()
            self.model.set_weights(current_global_weights)

        # officially start the training process
        # quit after a number of epoch
        LOGGER.info("=" * 40)
        LOGGER.info("ClientModel Start Training")
        LOGGER.info("=" * 40)

        for i in range(self.model.epoch):
            self._local_epoch += 1
            # record some info of the training process
            batch_num = 0
            # if user require
            # Tracking the training process every x samples 
            # x define by user
            if self._tracking_period is not None:
                self._tracking_point = self._tracking_period
                self._multiplier = 1

            # training per several epoch
            LOGGER.info(f"Enter epoch {self._local_epoch}")

            # reset loss and per after each epoch
            self.model.reset_train_loss()
            self.model.reset_train_performance()
            self.model.reset_test_loss()
            self.model.reset_test_performance()

            for images, labels in self.model.train_ds:
                batch_num += 1

                # Tracking the training process every x samples 
                # x define by user as trakcing_period
                if self._tracking_period is not None:
                    self._tracking_training_process(batch_num)

                # get the previous weights before the new training process within each batch
                self.model.previous_weights = self.model.get_weights()
                # training normally
                self._train_acc, self._train_loss = self.model.fit(images, labels)

                # merging when receiving a new global model
                if self._new_model_flag:
                    # before the merging process happens, need to retrieve current weights and global weights
                    # previous, current and global weights are used in the merged process

                    # update some tracking info
                    self._previous_merged_global_version = self._previous_global_version
                    self._merged_global_version = self._current_global_version

                    self.model.current_weights = self.model.get_weights()
                    # load global weights from file
                    LOGGER.info("=" * 20)
                    LOGGER.info("THIS IS INTENDED")
                    LOGGER.info("=" * 20)

                    self.model.global_weights = self._load_weights_from_file(self._global_model_name, Config.TMP_GLOBAL_MODEL_FOLDER)

                    LOGGER.info(f"New model ? - {self._new_model_flag}")
                    LOGGER.info(
                        f"Merging process happens at epoch {self._local_epoch}, batch {batch_num} when receiving the global version {self._merged_global_version}, current global version {self._previous_merged_global_version}")
                    # merging
                    self.__merge()
                    # changing flag status
                    self._new_model_flag = False


            if self.model.test_ds:
                for test_images, test_labels in self.model.test_ds:
                    self._test_acc, self._test_loss = self.model.evaluate(test_images, test_labels)
            else:
                self._test_acc, self._test_loss = 0.0, 0.0


            LOGGER.info("*" * 20)
            LOGGER.info(
                f'Epoch: {self._local_epoch}'
                f'\tLast Batch Train Accuracy: {(self._train_acc * 100):.4f}, '
                f'\tLast Batch Train Loss: {self._train_loss:.4f}, '
                f'\tLast Batch Test Accuracy: {(self._test_acc * 100):.4f}, '
                f'\tLast Batch Test Loss: {self._test_loss:.4f}'
            )
            LOGGER.info("*" * 20)

            if (self._min_acc <= self._train_acc) or (self._min_epoch <= self._local_epoch):
                self.__notify_local_model_to_server()
            else:
                LOGGER.info("*" * 20)
                LOGGER.info(f"At epoch {self._local_epoch}, current train acc is {self._train_acc:.4f}, which does not meet either the min acc {self._min_acc} or min epoch {self._min_epoch} to notify model to server")
                LOGGER.info("*" * 20)

            # break before completing the intended number of epoch
            # if the total training time excess some degree
            # set by client
            # if self.model.delta_time:
            #     delta_time = datetime.now() - start_time
            #     delta_time_in_minute = delta_time.total_seconds() / 60
            #     if delta_time_in_minute >= self.model.delta_time:
            #         break
            
    def test(self):
        current_global_weights = self._load_weights_from_file(self._global_model_name, Config.TMP_GLOBAL_MODEL_FOLDER)
        try:
            self.model.set_weights(current_global_weights)
        except Exception as e:
            LOGGER.info("=" * 20)
            LOGGER.info(e)
            LOGGER.info("=" * 20)
            self._get_model_dim_ready()
            self.model.set_weights(current_global_weights)

        # reset after each global version
        self.model.reset_test_loss()
        self.model.reset_test_performance()
        
        LOGGER.info('Testing the model')
        for test_images, test_labels in tqdm(self.model.test_ds):
            performance, loss = self.model.evaluate(test_images, test_labels)

        content = NotifyEvaluation(self._global_model_name, performance, loss)
        LOGGER.info("*" * 20)
        LOGGER.info(content.__dict__)
        LOGGER.info("*" * 20)
        message = MessageV2(
            headers={'timestamp': time_now(), 'message_type': Config.CLIENT_NOTIFY_EVALUATION, 'session_id': self._session_id, 'client_id': self._client_id},
            content=content
        ).to_json()
        
        self.queue_producer.send_data(message)

        self._new_model_flag = False

        if performance > self._expected_performance or loss < self._expected_loss:
            message = MessageV2(
                headers={'timestamp': time_now(), 'message_type': Config.CLIENT_NOTIFY_STOP, 'session_id': self._session_id, 'client_id': self._client_id},
                content=RequireStop(self._global_model_name, performance, loss)
            )
        

    def __notify_local_model_to_server(self):
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
                LOGGER.info("*" * 20)
                LOGGER.info('Notify new model to the server')
                message = MessageV2(
                        headers={"timestamp": time_now(), "message_type": Config.CLIENT_NOTIFY_MESSAGE, "client_id": self._client_id, "session_id": self._session_id},
                        content=NotifyModel(remote_worker_weight_path=remote_file_path, 
                                            filename=filename,
                                            global_version_used=self._merged_global_version, 
                                            loss=self._train_loss,
                                            performance= self._train_acc)).to_json()
                
                self.queue_producer.send_data(message)
                self._update_profile()
                LOGGER.info(message)
                LOGGER.info('Notify new model to the server successfully')
                LOGGER.info("*" * 20)
                break

    def __merge(self):
        LOGGER.info("MERGER weights.")
        # updating the value of each parameter of the local model
        # calculating the different to decide the formula of updating
        # calculation is performed on each corresponding layout
        # the different between the current weight and the previous weights
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
        data_depend = (1 - self._beta) * (local_qod * local_size) / (local_qod * local_size + global_qod * global_size)
        loss_depend = self._beta * global_loss / (local_loss + global_loss)
        alpha = data_depend + loss_depend

        LOGGER.info("-" * 20)
        LOGGER.info(f"local loss: {local_loss}")
        LOGGER.info(f"global loss: {global_loss}")
        LOGGER.info(f"local size: {local_size}")
        LOGGER.info(f"global data size: {global_size}")
        LOGGER.info(f"alpha = {alpha}")
        LOGGER.info("-" * 20)

        # create a blank array to store the result
        self.model.merged_weights = [np.zeros(layer.shape, dtype=np.float32) for layer in self.model.current_weights]
        # base on the direction, global weights and current local weights
        # updating the value of each parameter to get the new local weights (from merging process)
        for i, (local_layer, global_layer, direction_layer) in enumerate(zip(self.model.current_weights, self.model.global_weights, self.model.direction)):
            # access each element in each layer
            # np.where(condition, true, false)
            self.model.merged_weights[i] = np.where(direction_layer >= 0, global_layer, (1 - alpha) * global_layer + alpha * local_layer)


        # set the merged_weights to be the current weights of the model
        self.model.set_weights(self.model.merged_weights)


    def _get_model_dim_ready(self):
        if self._role == "train":
            ds = self.model.train_ds
        else:
            ds = self.model.test_ds
        for images, labels in ds:
            self.model.fit(images, labels)
            break
        
       
    def _load_weights_from_file(self, file_name, folder):
        full_path = folder + file_name
        while not os.path.isfile(full_path):
            LOGGER.info("*" * 20)
            LOGGER.info("Sleep 5 second when the the download process is not completed, then retry")
            LOGGER.info(full_path)
            LOGGER.info("*" * 20)
            sleep(5)

        with open(full_path, "rb") as f:
            weights = pickle.load(f)
        return weights
    
    def _tracking_training_process(self, batch_num):
        total_trained_sample = batch_num * self._batch_size
        if total_trained_sample > self._tracking_point:
            LOGGER.info(f"Training up to {total_trained_sample} samples")
            self._multiplier += 1
            self._tracking_point = self._tracking_point * self._multiplier
