import os, sys
import json
import logging
from threading import Thread, Lock
import uuid
from time import sleep

import re
import pickle
from tqdm import tqdm


from asynfed.common.messages import ExchangeMessage


from asynfed.common.config import LocalStoragePath, MessageType
from asynfed.common.messages.client import ClientInitConnection, DataDescription, SystemInfo, ResponseToPing
from asynfed.common.messages.client import ClientModelUpdate, NotifyEvaluation, TesterRequestStop
from asynfed.common.messages.server import ServerModelUpdate
import asynfed.common.utils.time_ultils as time_utils 


from asynfed.common.messages.server.server_response_to_init import ServerRespondToInit, StorageInfo
import asynfed.common.messages as message_utils




from .objects import ModelWrapper, LocalModelUploadInfo, ServerTrainingConfig
from .config_structure import ClientConfig
from .components import ClientComponents

import concurrent.futures
thread_pool_ref = concurrent.futures.ThreadPoolExecutor


LOGGER = logging.getLogger(__name__)
logging.getLogger('pika').setLevel(logging.WARNING)
LOGGER.setLevel(logging.INFO)

lock = Lock()


from .objects import GlobalModelInfo

class ClientState(object):
    def __init__(self):
        # control the state of download process
        self.is_connected = False
        self.training_thread_is_running = False
        self.publish_new_local_update_is_running = False
        self.is_stop_condition = False
        self.new_model_flag = False


class TrainingProcessInfo(object):
    '''
    the information that change periodically during the training process
    '''
    def __init__(self):
        self.global_chosen_list: list = []
        self.previous_global_version_used = 0
        self.global_version_used: int = 0

        self.local_epoch = 0
        self.train_acc = 0.0
        self.train_loss = 0.0


from abc import ABC, abstractmethod

# class Client(object):
class Client(ABC):
    def __init__(self, model: ModelWrapper, config: dict):
        """
        config structure can be found at client_config.py file

        """
        self._config: ClientConfig = self._load_config_info(config= config)
        self._local_storage_path: LocalStoragePath = self._get_local_storage_path()

        self._config.session_id = ""

        # initial the state of client
        self._state = ClientState()
        self._training_process_info = TrainingProcessInfo()


        # --------- info get from server ------------
        # just initialize these property when receiving respone from server for the first time
        self._global_model_info: GlobalModelInfo = None
        self._server_training_config: ServerTrainingConfig = None
        self._remote_upload_folder: str = None

        # dynamic - training process
        # local model update info object
        self._local_model_upload_info: LocalModelUploadInfo = LocalModelUploadInfo()


        # fixed property
        self._model = model
        self._config.dataset.data_size = self._config.dataset.data_size or self._model.data_size
        self._config.dataset.qod = self._config.dataset.qod or self._model.qod


        LOGGER.info("Client config for training process")
        message_utils.print_message(self._config.to_dict())


        # load components of client: queue, storage cleaner
        # the cloud storage will be loaded later when received info from server
        storage_cleaner_conf = {"global_model_folder": self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER,
                                "local_model_folder": self._local_storage_path.LOCAL_MODEL_ROOT_FOLDER}
        self._components = ClientComponents(host_object= self, queue_consumer_conf= self._config.queue_consumer,
                                            queue_producer_conf= self._config.queue_producer,
                                            storage_cleaner_conf= storage_cleaner_conf)


        # thread
        self._thread_consumer = Thread(target= self._start_consumer, name= "client_consumer_thread")
        self._clean_storage_thread = Thread(target= self._clean_storage, name= "client_clean_storage_thread")
        self._clean_storage_thread.daemon = True



        LOGGER.info("-" * 40)
        LOGGER.info(f'Client Id: {self._config.client_id}')
        LOGGER.info(f'Consumer Queue')
        message_utils.print_message(self._config.queue_consumer.to_dict())
        LOGGER.info(f'Producer Queue')
        message_utils.print_message(self._config.queue_producer.to_dict()) 
        LOGGER.info("-" * 40)


        # send message to server for connection
        self._send_init_message()

    @abstractmethod
    def _train(self):
        pass

    # Run the client
    def start(self):
        LOGGER.info("CLIENT STARTS")
        self._thread_consumer.start()
        self._clean_storage_thread.start()

        while not self._state.is_stop_condition:
            # check the stop condition every 300 seconds
            sleep(300)
        sys.exit(0)


    # consumer queue callback
    def on_message_received(self, ch, method, props, body):
        msg_received: dict = message_utils.deserialize(body.decode('utf-8'))
        message_type: str = msg_received['headers']['message_type']

        # these two abstract method
        # handle differently by each algorithm
        if message_type == MessageType.SERVER_INIT_RESPONSE and not self._state.is_connected:
            self._handle_server_init_response(msg_received)


        elif message_type == MessageType.SERVER_NOTIFY_MESSAGE and self._state.is_connected:
            self._handle_server_notify_message(msg_received)


        elif message_type == MessageType.SERVER_PING_TO_CLIENT:
            self._handle_server_ping_to_client(msg_received)


        elif message_type == MessageType.SERVER_STOP_TRAINING: 
            message_utils.print_message(msg_received)
            self._state.is_stop_condition = True
            sys.exit(0)


    # cloud storage callback
    # report result on parent process
    def on_download(self, result):
        pass

    def on_upload(self, result):
        pass



    def _test(self):
        current_global_model_file_name = self._global_model_info.get_file_name()
        
        file_exist, current_global_weights = self._load_weights_from_file(folder= self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER,
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

            # reset state after testing each global model
            self._model.reset_test_loss()
            self._model.reset_test_performance()
            
            LOGGER.info('Testing the model')
            for test_images, test_labels in tqdm(self._model.test_ds):
                performance, loss = self._model.evaluate(test_images, test_labels)

            headers = self._create_headers(message_type= MessageType.CLIENT_NOTIFY_EVALUATION)

            remote_storage_path = self._global_model_info.get_full_remote_file_path()

            notify_evaluation_message: NotifyEvaluation = NotifyEvaluation(remote_storage_path= remote_storage_path,
                                                                           performance= performance, loss= loss)


            LOGGER.info("*" * 20)
            LOGGER.info(notify_evaluation_message.to_dict())
            LOGGER.info("*" * 20)
            message = ExchangeMessage(headers= headers, content= notify_evaluation_message.to_dict()).to_json()
            self._components.queue_producer.send_data(message)

            # # check the stop conditions
            # if performance > self._config.model_config.stop_conditions.expected_performance or loss < self._config.model_config.stop_conditions.expected_loss:
            #     headers = self._create_headers(message_type= MessageType.CLIENT_NOTIFY_STOP)

            #     content = TesterRequestStop(remote_storage_path, performance, loss).to_dict()
            #     message = ExchangeMessage(headers= headers, content= content).to_json()
            #     self._components.queue_producer.send_data(message)
        

    # queue handling functions
    def _handle_server_init_response(self, msg_received):
        LOGGER.info("Server Response to Init Message")
        message_utils.print_message(msg_received)
        
        content = msg_received['content']
        server_init_response: ServerRespondToInit = ServerRespondToInit(**content)

        session_id = msg_received['headers']['session_id']
        reconnect = msg_received['headers']['reconnect']

        if reconnect:
            LOGGER.info("=" * 40)
            LOGGER.info("Reconnect to server.")
            LOGGER.info("=" * 40)

        self._config.session_id = session_id

        self._server_training_config = ServerTrainingConfig(strategy= server_init_response.strategy,
                                        exchange_at= server_init_response.model_info.exchange_at.to_dict(),
                                        epoch_update_frequency= server_init_response.epoch_update_frequency)

        # initialize client algorithm from here

        # get the exchange condition from server

        remote_global_folder: str = f"{server_init_response.model_info.global_folder}/{server_init_response.model_info.name}"

        self._file_extension: str = server_init_response.model_info.file_extension


        # connect to cloud storage service provided by server
        storage_info: StorageInfo = server_init_response.storage_info
        self._cloud_storage_type = storage_info.type

        # self._config.
        self._remote_upload_folder: str = storage_info.client_upload_folder


        self._components.add_cloud_storage(storage_info= storage_info)

        self._state.is_connected = True

        file_name = f"{server_init_response.model_info.version}.{self._file_extension}"
        remote_path = f"{remote_global_folder}/{file_name}"

        # Check whether it is a new global model to arrive
        file_exists = self._components.cloud_storage.is_file_exists(file_path= remote_path)

        # initialize the global model information
        self._global_model_info = GlobalModelInfo(remote_folder_path= remote_global_folder, 
                                                name = server_init_response.model_info.name, 
                                                version= server_init_response.model_info.version, 
                                                file_extension= server_init_response.model_info.file_extension)
        
        if file_exists:
            LOGGER.info("*" * 20)
            LOGGER.info(f"{remote_path} exists in the cloud. Let's begin training!")
            LOGGER.info("*" * 20)

            
            # download_success = False

            # if self._global_model_info.version < server_init_response.model_info.version:
            # LOGGER.info("Detect new global version.")
            local_path = os.path.join(self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, file_name)

            # to make sure the other process related to the new global model version start
            # only when the downloading process success
            download_success = self._attempt_to_download(remote_file_path= remote_path, local_file_path= local_path)


            if download_success:
                # update only downloading process is success
                LOGGER.info(f"Successfully downloaded global model {self._global_model_info.name}, version {self._global_model_info.version}")
                # # update info in profile file
                # self._update_profile()

                if self._config.role == "trainer":
                    self._start_training_thread()

                # for testing, do not need to start thread
                # because tester just test whenever it receive new model 
                elif self._config.role == "tester":
                    self._test()

                # if not os.path.exists(self._profile_file_name):
                #     self._create_profile()
                # else:
                #     self._load_profile()
        else:
            LOGGER.info("*" * 20)
            LOGGER.info(f"{remote_path} does not exist in the cloud. Fail to start training thread for the first time")
            LOGGER.info("*" * 20)



    def _handle_server_notify_message(self, msg_received):
        message_utils.print_message(msg_received)
        server_model_udpate: ServerModelUpdate = ServerModelUpdate(**msg_received['content'])

        # check whether the client is chosen to engage in this training epoch
        # default status for tester is true
        is_chosen = True
        if self._config.role == "trainer":
            self._training_process_info.global_chosen_list = server_model_udpate.worker_id
            is_chosen = self._config.client_id in self._training_process_info.global_chosen_list or not self._training_process_info.global_chosen_list

        if is_chosen:
            with lock:
                # attempt to download the global model
                # for cloud storage, always use forward slash
                # regardless of os
                file_name = f"{server_model_udpate.global_model.version}.{self._file_extension}"
                remote_path = f'{self._global_model_info.remote_folder_path}/{file_name}'


                local_path = os.path.join(self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, file_name)

                file_exists = self._components.cloud_storage.is_file_exists(file_path= remote_path)
                
                download_success = False

                if file_exists:
                    LOGGER.info("*" * 20)
                    LOGGER.info(f"{remote_path} exists in the cloud. Start updating new global model process")
                    LOGGER.info("*" * 20)
                    # to make sure the other process related to the new global model version start
                    # only when the downloading process success
                    download_success = self._attempt_to_download(remote_file_path= remote_path, local_file_path= local_path)
                else:
                    # download_success = False
                    LOGGER.info("*" * 20)
                    LOGGER.info(f"{remote_path} does not exist in the cloud. Ignore this server update message")
                    LOGGER.info("*" * 20)

            if download_success:
                # Only update info when download is success
                # update local version (the latest global model that the client have)
                self._global_model_info.update(**server_model_udpate.global_model.to_dict())


                LOGGER.info(f"Successfully downloaded new global model {self._global_model_info.name}, version {self._global_model_info.version}")
                # print the content only when succesfully download new model
                message_utils.print_message(server_model_udpate.to_dict())

                if self._config.role == "tester":
                    # test everytime receive new global model notify from server
                    self._test()

                elif self._config.role == "trainer":
                    LOGGER.info(f"{self._config.client_id} is chosen to train for global model version {self._global_model_info.version}")

                    # if the training thread does not start yet 
                    # (fail to download the global model in the response to init message from server)
                    # start now
                    # else just update the state of the new model flag
                    if self._state.training_thread_is_running:
                        self._state.new_model_flag = True
                    else:
                        self._start_training_thread()



    def _handle_server_ping_to_client(self, msg_received):
        if msg_received['content']['client_id'] == self._config.client_id:
            message_utils.print_message(msg_received)
            headers = self._create_headers(message_type= MessageType.CLIENT_PING_MESSAGE)
            message = ExchangeMessage(headers= headers, content=ResponseToPing().to_dict()).to_json()
            self._components.queue_producer.send_data(message)


    def _start_publish_new_local_update_thread(self):
        LOGGER.info("*" * 40)
        LOGGER.info("Publish New Local Model Thread is Runnning!")
        LOGGER.info("*" * 40)
        self._state.publish_new_local_update_is_running = True

        publish_new_local_update_thread = Thread(target= self._publish_new_local_update, name= "client_publish_new_local_update_thread")
        publish_new_local_update_thread.daemon = True

        publish_new_local_update_thread.start()


    def _publish_new_local_update(self):
        while True:
            # check every 10 second for whether there is a new model
            sleep(10)
            if self._local_model_upload_info.new_update:
                self._local_model_upload_info.new_update = False
                while True:
                    # make a copy of the latest local model udpate and send it
                    new_update_info: LocalModelUploadInfo = LocalModelUploadInfo(**self._local_model_upload_info.to_dict())
                    with open(new_update_info.local_weight_path, 'wb') as f:
                        pickle.dump(new_update_info.weight_array, f)

                    LOGGER.info(f'Saved new local model {new_update_info.filename} to {new_update_info.local_weight_path}')
  
                    if self._components.cloud_storage.upload(local_file_path= new_update_info.local_weight_path, 
                                                remote_file_path= new_update_info.remote_weight_path) is True:
                
                        # After training, notify new model to the server.
                        LOGGER.info("*" * 20)
                        LOGGER.info('Notify new model to the server')
                        headers= self._create_headers(message_type= MessageType.CLIENT_NOTIFY_MESSAGE)

                        notify_local_model_message: ClientModelUpdate = ClientModelUpdate(
                                                    storage_path=new_update_info.remote_weight_path, 
                                                    file_name=new_update_info.filename,
                                                    global_version_used=new_update_info.global_version_used, 
                                                    loss=new_update_info.train_loss,
                                                    performance=new_update_info.train_acc)
                        
                        message = ExchangeMessage(headers= headers, content= notify_local_model_message.to_dict()).to_json()
                        
                        self._components.queue_producer.send_data(message)
                        # self._update_profile()
                        LOGGER.info(message)
                        LOGGER.info('Notify new model to the server successfully')
                        LOGGER.info("*" * 20)

                        break



    def _load_config_info(self, config: dict) -> ClientConfig:
        # for multiple user to run on the same queue, 
        # set bucket name to be the queue name
        # and also the queue exchange name
        # user may already set in the run file, but just to make sure that it is set
        queue_exchange = config['queue_exchange']


        client_id = config['client_id'] or str(uuid.uuid4())
        config['queue_consumer']['queue_name'] = f"queue_{client_id}_{config['queue_exchange']}"

        client_publish_queue_name = f"server-listen-queue-{queue_exchange}"
        config['queue_producer']['queue_name'] = config['queue_producer']['queue_name'] or client_publish_queue_name

        if not config['queue_consumer']['queue_exchange']:
            config['queue_consumer']['queue_exchange'] = queue_exchange
            config['queue_producer']['queue_exchange'] = queue_exchange

        return ClientConfig(**config)

    def _get_local_storage_path(self) -> LocalStoragePath:
        # create local folder for storage
        # get the current folder path, then save all local file within the current folder
        # full_path = os.path.join(os.getcwd(), self._config.record_root_folder, self._config.client_id)
        full_path = os.path.join(os.getcwd(), self._config.client_id)

        # Initialize a profile file for client
        # self._profile_file_name = os.path.join(full_path, "profile.json")


        return LocalStoragePath(root_folder= full_path, save_log= self._config.save_log)


    def _send_init_message(self):
        data_description = {
            'size': self._config.dataset.data_size,
            'qod': self._config.dataset.qod,
        }

        client_init_message: ClientInitConnection = ClientInitConnection(
                                                    role=self._config.role,
                                                    system_info= SystemInfo().to_dict(),
                                                    data_description=DataDescription(**data_description).to_dict()
                                                    )
        

        headers = self._create_headers(message_type= MessageType.CLIENT_INIT_MESSAGE)
        message = ExchangeMessage(headers= headers, content= client_init_message.to_dict()).to_json()
        self._components.queue_producer.send_data(message)



    def _start_consumer(self):
        self._components.queue_consumer.start()

    def _start_training_thread(self):
        LOGGER.info("Start training thread.")
        self._state.training_thread_is_running = True
        training_thread = Thread(target= self._train, name= "client_training_thread")
        training_thread.daemon = True

        training_thread.start()


    def _clean_storage(self):
        LOGGER.info("CLEANING STORAGE THREAD IS RUNNING")
        while True:
            sleep(self._config.cleaning_config.clean_storage_period)
            LOGGER.info("CLEANING TIME")

            # -------- Global Weight File Cleaning ------------ 
            global_threshold = self._global_model_info.version - self._config.cleaning_config.global_keep_version_num
            self._components.storage_cleaner.delete_local_files(is_global_folder= True, threshold= global_threshold)

            # -------- Client weight files cleaning -----------
            if self._config.role == "trainer":
                local_threshold = self._training_process_info.local_epoch - self._config.cleaning_config.local_keep_version_num
                self._components.storage_cleaner.delete_local_files(is_global_folder= False, threshold= local_threshold)




    def _attempt_to_download(self, remote_file_path: str, local_file_path: str) -> bool:
        LOGGER.info("Downloading new global model............")

        for i in range(self._config.download_attempt):
            if self._components.cloud_storage.download(remote_file_path= remote_file_path, 
                                            local_file_path= local_file_path):
                return True
            
            LOGGER.info(f"{i + 1} attempt: download model failed, retry in 5 seconds.")

            i += 1
            if i == self._config.download_attempt:
                LOGGER.info(f"Already try {self._config.download_attempt} time. Pass this global version: {remote_file_path}")
            sleep(5)

        return False
    

    def _create_headers(self, message_type: str) -> dict:
        headers = {'timestamp': time_utils.time_now(), 'message_type': message_type, 'session_id': self._config.session_id, 'client_id': self._config.client_id}
        return headers

    # # profile related
    # def _create_message(self):
    #     data = {
    #         "session_id": self._config.session_id,
    #         "client_id": self._config.client_id,
    #         "global_model_name": self._global_model_info.name or None,
    #         "local_epoch": self._training_process_info.local_epoch,
    #         "local_qod": self._config.dataset.qod,
    #         "save_global_model_version": self._global_model_info.version,
    #         "save_global_model_update_data_size": self._global_model_update_data_size,
    #         "save_global_avg_loss": self._global_avg_loss,
    #         "save_global_avg_qod": self._global_avg_qod,
    #     }
    #     return data

    # def _create_profile(self):
    #     data = self._create_message()
    #     with open(self._profile_file_name, 'w') as outfile:
    #         json.dump(data, outfile)

    # def _update_profile(self):
    #     data = self._create_message()
    #     with open(self._profile_file_name, "w") as outfile:
    #         json.dump(data, outfile)

    # # load client information from profile.json function
    # def _load_profile(self):
    #     try:
    #         with open(self._profile_file_name) as json_file:
    #             data = json.load(json_file)
    #             self._config.session_id = data["session_id"]
    #             self._config.client_id = data["client_id"]
    #             self._global_model_name = data["global_model_name"]
    #             self._.local_epoch = data["local_epoch"]
    #             self._local_qod = data["local_qod"]

    #             self._save_global_model_version = data["save_global_model_version"]
    #             self._save_global_model_update_data_size = data["save_global_model_update_data_size"]
    #             self._save_global_avg_loss = data["save_global_avg_loss"]
    #             self._save_global_avg_qod = data["save_global_avg_qod"]


    #     except Exception as e:
    #         LOGGER.info(e)


    def _extract_version(self, folder_path):
        match = re.search(rf"(\d+){re.escape(self._file_extension)}$", folder_path)
        if match:
            return int(match.group(1))
        else:
            return None
        

    def _get_model_dim_ready(self):
        if self._config.role == "trainer":
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


    def _update_new_local_model_info(self):
        if not self._state.publish_new_local_update_is_running:
            self._start_publish_new_local_update_thread()
            
        # Save weights locally after training
        filename = f'{self._training_process_info.local_epoch}.{self._file_extension}'
        
        save_location = os.path.join(self._local_storage_path.LOCAL_MODEL_ROOT_FOLDER, filename)
        # for the remote storage path, use forwawrd slash as the separator
        # regardless of os
        remote_file_path = f"{self._remote_upload_folder}/{filename}"

        self._local_model_upload_info.update(weight_array= self._model.get_weights(), 
                                            filename= filename, local_weight_path= save_location, 
                                            global_version_used= self._training_process_info.global_version_used,
                                            remote_weight_path= remote_file_path,
                                            train_acc= self._training_process_info.train_acc, train_loss= self._training_process_info.train_loss)

