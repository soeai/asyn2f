
import os
import logging
from typing import List
import numpy as np
from tqdm import tqdm
import pickle

from time import sleep 

from asynfed.commons.messages import Message
from asynfed.commons.config import MessageType


from asynfed.commons.messages.client import ClientModelUpdate, NotifyEvaluation, TesterRequestStop

from asynfed.client import Client



LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)



# This is the proposed federated asynchronous training algorithm of our paper
# More algorithms can be found at other files in this directory 
class MStepFedAsync(Client):
    def __init__(self, model, config: dict):
        super().__init__(model, config)
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



    def _train(self):
        self._tracking_period = self._config.tracking_point
        
        # for notifying global version used to server purpose
        self._merged_global_version = self._current_global_version

        # for tensorflow model, there is some conflict in the dimension of 
        # an initialized model and al already trained one
        # fixed this problem
        # by training the model before loading the global weights
        file_exist, current_global_weights = self._load_weights_from_file(self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self._global_model_name)

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
                self._local_epoch += 1
                batch_num = 0
                # training per several epoch
                LOGGER.info(f"Enter epoch {self._local_epoch}")

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
                    self._train_acc, self._train_loss = self._model.fit(images, labels)

                    # Tracking the training process every x samples 
                    # x define by user as trakcing_period
                    if self._tracking_period is not None:
                        self._tracking_training_process(batch_num)

                    # merging when receiving a new global model
                    if self._new_model_flag:
                        # update some tracking info
                        self._previous_merged_global_version = self._previous_global_version
                        self._merged_global_version = self._current_global_version

                        # before the merging process happens, need to retrieve current weights and global weights
                        # previous, current and global weights are used in the merged process
                        self._model.current_weights = self._model.get_weights()
                        # load global weights from file
                        file_exist, self._model.global_weights = self._load_weights_from_file(self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self._global_model_name)
                        
                        
                        if file_exist:
                            LOGGER.info(f"New model ? - {self._new_model_flag}")
                            LOGGER.info(
                                f"Merging process happens at epoch {self._local_epoch}, batch {batch_num} when receiving the global version {self._merged_global_version}, current global version {self._previous_merged_global_version}")
                                
                            # changing flag status
                            self._new_model_flag = False
                            # merging
                            self._merge()

                        # if not file_exist, also changing the flag status
                        self._new_model_flag = False


                if self._model.test_ds:
                    for test_images, test_labels in self._model.test_ds:
                        self._test_acc, self._test_loss = self._model.evaluate(test_images, test_labels)
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
                    self._update_new_local_model_info()

                else:
                    LOGGER.info("*" * 20)
                    LOGGER.info(f"At epoch {self._local_epoch}, current train acc is {self._train_acc:.4f}, which does not meet either the min acc {self._min_acc} or min epoch {self._min_epoch} to notify model to server")
                    LOGGER.info("*" * 20)


            
    def _test(self):
        file_exist, current_global_weights = self._load_weights_from_file(self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self._global_model_name)
        if file_exist:
            try:
                self._model.set_weights(current_global_weights)
            except Exception as e:
                LOGGER.info("=" * 20)
                LOGGER.info(e)
                LOGGER.info("=" * 20)
                self._get_model_dim_ready()
                self._model.set_weights(current_global_weights)

            # reset state after testing each global model
            self._model.reset_test_loss()
            self._model.reset_test_performance()
            
            LOGGER.info('Testing the model')
            for test_images, test_labels in tqdm(self._model.test_ds):
                performance, loss = self._model.evaluate(test_images, test_labels)

            headers = self._create_headers(message_type= MessageType.CLIENT_NOTIFY_EVALUATION)
            notify_evaluation_message: NotifyEvaluation = NotifyEvaluation(self._global_model_name, performance, loss)
            LOGGER.info("*" * 20)
            LOGGER.info(notify_evaluation_message.to_dict())
            LOGGER.info("*" * 20)
            message = Message(headers= headers, content= notify_evaluation_message.to_dict()).to_json()
            self._queue_producer.send_data(message)


            # # check the stop conditions
            # if performance > self._config.stop_conditions.expected_performance or loss < self._config.stop_conditions.expected_loss:
            #     headers = self._create_headers(message_type= MessageType.CLIENT_NOTIFY_STOP)
            #     content = content=TesterRequestStop(self._global_model_name, performance, loss).to_dict()
            #     message = Message(headers= headers, content= content).to_json()
            #     self._queue_producer.send_data(message)
        


    def _update_new_local_model_info(self):
        if not self._publish_new_local_update_is_running:
            self._start_publish_new_local_update_thread()
            
        # Save weights locally after training
        filename = f'{self._config.client_id}_v{self._local_epoch}.pkl'
        save_location = os.path.join(self._local_storage_path.LOCAL_MODEL_ROOT_FOLDER, filename)
        remote_file_path = os.path.join("clients", self._config.client_id, filename)

        self._local_model_update_info.update(weight_array= self._model.get_weights(), 
                                            filename= filename, local_weight_path= save_location, 
                                            global_version_used= self._merged_global_version,
                                            remote_weight_path= remote_file_path,
                                            train_acc= self._train_acc, train_loss= self._train_loss)



    def _merge(self):
        LOGGER.info("MERGER weights.")


        # set the merged_weights to be the current weights of the model
        self._model.set_weights(self._model.global_weights)


    def _get_model_dim_ready(self):
        if self._config.role == "train":
            ds = self._model.train_ds
        else:
            ds = self._model.test_ds
        for images, labels in ds:
            self._model.fit(images, labels)
            break
        
       
    def _load_weights_from_file(self, folder: str, file_name: str):
        full_path = os.path.join(folder, file_name)

        file_exist = os.path.isfile(full_path)
        if not file_exist:
            LOGGER.info("error in either downloading process or opening file in local. Please check again")

        weights = []
        if file_exist:
            with open(full_path, "rb") as f:
                weights: List = pickle.load(f)

        return file_exist, weights
    
    def _tracking_training_process(self, batch_num):
        total_trained_sample = batch_num * self._config.training_params.batch_size
        if total_trained_sample > self._tracking_point:
            LOGGER.info(f"Training up to {total_trained_sample} samples")
            self._multiplier += 1
            self._tracking_point = self._tracking_period * self._multiplier
