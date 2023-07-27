
# import os
# import logging
# from typing import List
# import numpy as np
# from tqdm import tqdm
# import pickle

# from time import sleep 

# from asynfed.common.messages import ExchangeMessage
# from asynfed.common.config import MessageType


# from asynfed.common.messages.client import ClientModelUpdate, NotifyEvaluation, TesterRequestStop

# from asynfed.client import Client



# LOGGER = logging.getLogger(__name__)
# LOGGER.setLevel(logging.INFO)



# # This is the proposed federated asynchronous training algorithm of our paper
# # More algorithms can be found at other files in this directory 
# class KAFLMStepClient(Client):
#     def __init__(self, model, config: dict):
#         super().__init__(model, config)
#         '''
#         - model must be an instance of an inheritant of class ModelWrapper
#         - for train
#             - model.train_ds: require 
#             - model.test_ds: optional
#         - for tester: test_ds is required

#         - train_ds and test_ds must in a format of a list of several batches
#             each batch contain x, y
#         - detail instruction (use as reference) of how to create a tensorflow model 
#             is found at asynfed/client/tensorflow/tensorflow_framework
#         - user is freely decided to follow the sample
#             or create their own model in their own platform (pytorch,...)
#         '''



#     def _train(self):
#         self._tracking_period = self._config.tracking_point
        
#         # for notifying global version used to server purpose
#         self._global_version_used = self._current_global_version

#         # for tensorflow model, there is some conflict in the dimension of 
#         # an initialized model and al already trained one
#         # fixed this problem
#         # by training the model before loading the global weights
#         current_global_model_file_name = self._get_current_global_model_file_name()
#         file_exist, current_global_weights = self._load_weights_from_file(self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, 
#                                                                           file_name= current_global_model_file_name)

#         if file_exist:
#             try:
#                 self._model.set_weights(current_global_weights)
#             except Exception as e:
#                 LOGGER.info("=" * 20)
#                 LOGGER.info(e)
#                 LOGGER.info("=" * 20)
#                 self._get_model_dim_ready()
#                 self._model.set_weights(current_global_weights)

#             # officially start the training process
#             # quit after a number of epoch
#             LOGGER.info("=" * 40)
#             LOGGER.info("ClientModel Start Training")
#             LOGGER.info("=" * 40)
#             if self._new_model_flag:
#                 # update some tracking info
#                 self._previous_global_version_used = self._previous_global_version
#                 self._global_version_used = self._current_global_version

#                 # before the merging process happens, need to retrieve current weights and global weights
#                 # previous, current and global weights are used in the merged process
#                 self._model.current_weights = self._model.get_weights()
#                 # load global weights from file
#                 current_global_model_file_name = self._get_current_global_model_file_name()
#                 file_exist, self._model.global_weights = self._load_weights_from_file(folder= self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, 
#                                                                                       file_name= current_global_model_file_name)
                
                
#                 if file_exist:
#                     LOGGER.info(f"New model ? - {self._new_model_flag}")
#                     LOGGER.info(
#                         f"Merging process happens at epoch {self._local_epoch}, batch {batch_num} when receiving the global version {self._global_version_used}, current global version {self._previous_global_version_used}")
                        
#                     # changing flag status
#                     self._new_model_flag = False
#                     # merging
#                     self._merge()

#                 # if not file_exist, also changing the flag status
#                 self._new_model_flag = False


#             for _ in range(self._model.epoch):
#                 # record some info of the training process
#                 self._local_epoch += 1
#                 batch_num = 0
#                 # training per several epoch
#                 LOGGER.info(f"Enter epoch {self._local_epoch}")

#                 # reset loss and per after each epoch
#                 self._model.reset_train_loss()
#                 self._model.reset_train_performance()
#                 self._model.reset_test_loss()
#                 self._model.reset_test_performance()

#                 # if user require
#                 # Tracking the training process every x samples 
#                 # x define by user
#                 if self._tracking_period is not None:
#                     self._tracking_point = self._tracking_period
#                     self._multiplier = 1

#                 # training in each batch
#                 for images, labels in self._model.train_ds:
#                     batch_num += 1
#                     # get the previous weights before the new training process within each batch
#                     self._model.previous_weights = self._model.get_weights()
#                     # training normally
#                     self._train_acc, self._train_loss = self._model.fit(images, labels)

#                     # Tracking the training process every x samples 
#                     # x define by user as trakcing_period
#                     if self._tracking_period is not None:
#                         self._tracking_training_process(batch_num)

#                     # merging when receiving a new global model

#                 if self._model.test_ds:
#                     for test_images, test_labels in self._model.test_ds:
#                         self._test_acc, self._test_loss = self._model.evaluate(test_images, test_labels)
#                 else:
#                     self._test_acc, self._test_loss = 0.0, 0.0


#                 LOGGER.info("*" * 20)
#                 LOGGER.info(
#                     f'Epoch: {self._local_epoch}'
#                     f'\tLast Batch Train Accuracy: {(self._train_acc * 100):.4f}, '
#                     f'\tLast Batch Train Loss: {self._train_loss:.4f}, '
#                     f'\tLast Batch Test Accuracy: {(self._test_acc * 100):.4f}, '
#                     f'\tLast Batch Test Loss: {self._test_loss:.4f}'
#                 )
#                 LOGGER.info("*" * 20)

#                 if (self._min_acc <= self._train_acc) or (self._min_epoch <= self._local_epoch):
#                     self._update_new_local_model_info()

#                 else:
#                     LOGGER.info("*" * 20)
#                     LOGGER.info(f"At epoch {self._local_epoch}, current train acc is {self._train_acc:.4f}, which does not meet either the min acc {self._min_acc} or min epoch {self._min_epoch} to notify model to server")
#                     LOGGER.info("*" * 20)


            
