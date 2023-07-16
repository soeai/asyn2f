import os, sys
import json
import logging
import threading
import uuid
from time import sleep
from abc import abstractmethod


from asynfed.commons.messages import Message
from asynfed.commons.conf import Config, init_config as _logging_config
from asynfed.commons.utils import AmqpConsumer, AmqpProducer
import asynfed.commons.utils.time_ultils as time_utils


from asynfed.commons.messages.client import ClientInitConnection, DataDescription, SystemInfo, ResponseToPing
from asynfed.commons.messages.server import ServerModelUpdate

from asynfed.commons.messages.server.server_response_to_init import ResponseToInit, StorageInfo
import asynfed.commons.messages.utils as message_utils 


from .client_storage_connector import ClientStorageAWS, ClientStorageMinio
from .ModelWrapper import ModelWrapper


import concurrent.futures
thread_pool_ref = concurrent.futures.ThreadPoolExecutor


LOGGER = logging.getLogger(__name__)
logging.getLogger('pika').setLevel(logging.WARNING)
LOGGER.setLevel(logging.INFO)

lock = threading.Lock()


class Client(object):
    # def __init__(self, model: ModelWrapper, config: dict, save_log: bool = True):
    def __init__(self, model: ModelWrapper, config: dict):
        _logging_config("client", config['save_log'])

        self._config = config
        self._role = self._config.get("role") or "train"

        # fixed property
        self._model = model

        self._local_data_size = self._model.data_size
        self._local_qod = self._model.qod

        # dynamic - training process
        self._local_epoch = 0
        self._train_acc = 0.0
        self._train_loss = 0.0

        # --------- info get from server ------------
        self._global_chosen_list = None
        # for updating new global model
        self._previous_global_version = 0
        self._current_global_version = 0
        self._received_global_version = 0

        self._global_model_name = None

        # stop condition received from server
        self._min_acc: float
        self._min_epoch: int
        self._is_stop_condition = False

        # merging process
        self._global_avg_loss = None
        self._global_avg_qod = None
        self._global_model_update_data_size = None

        self._session_id = ""
        # ---------------------

        self._client_id = self._config.get('client_id') or str(uuid.uuid4())

        # some boolean variable to track the state of client
        self._is_connected = False
        self._is_training = False
        self._new_model_flag = False

        # properties saved in profile file
        self._save_global_avg_qod = None
        self._save_global_avg_loss = None
        self._save_global_model_update_data_size = None
        self._save_global_model_version = None


        # Initialize profile for client
        if not os.path.exists("profile.json"):
            self._create_profile()
        else:
            self._load_profile()

        # specify a queue for each client
        self._config['queue_consumer']['queue_name'] = f"queue_{self._client_id}"

        # queue related
        self._queue_consumer = AmqpConsumer(self._config['queue_consumer'], self)
        self._thread_consumer = threading.Thread(target=self._start_consumer)
        self._queue_producer = AmqpProducer(self._config['queue_producer'])


        LOGGER.info(f'\n\nClient Id: {self._client_id}'
                    f'\n\tQueue In : {self._config["queue_consumer"]}'
                    f'\n\tQueue Out : {self._config["queue_producer"]}'
                    f'\n\n')

        # send message to server for connection
        self._send_init_message()



    # Run the client
    def start(self):
        self._thread_consumer.start()
        while not self._is_stop_condition:
            # check the stop condition every 300 seconds
            sleep(300)
        sys.exit(0)


    # consumer queue callback
    def on_message_received(self, ch, method, props, body):
        msg_received: dict = message_utils.deserialize(body.decode('utf-8'))
        message_type: str = msg_received['headers']['message_type']

        if message_type == Config.SERVER_INIT_RESPONSE and not self._is_connected:
            self._handle_server_init_response(msg_received)

        elif message_type == Config.SERVER_NOTIFY_MESSAGE and self._is_connected:
            self._handle_server_notify_message(msg_received)

        elif message_type == Config.SERVER_STOP_TRAINING: 
            message_utils.print_message(msg_received)
            self._is_stop_condition = True
            sys.exit(0)

        elif message_type == Config.SERVER_PING_TO_CLIENT:
            self._handle_server_ping_to_client(msg_received)


    # cloud storage callback
    # report result on parent process
    def on_download(self, result):
        if result:
            self._new_model_flag = True
            LOGGER.info(f"ON PARENT. Successfully downloaded new global model, version {self._current_global_version}")
        else:
            LOGGER.info("ON PARENT. Download model failed. Passed this version!")

    def on_upload(self, result):
        pass


    @abstractmethod
    def _train(self):
        pass

    @abstractmethod
    def _test(self):
        pass


    def _send_init_message(self):
        data_description = {
            'data_size': self._local_data_size,
            'qod': self._local_qod,
        }

        client_init_message: ClientInitConnection = ClientInitConnection(
                                                    role=self._role,
                                                    system_info= SystemInfo().to_dict(),
                                                    data_description=DataDescription(**data_description).to_dict()
                                                    )
        

        # headers = {'timestamp': time_utils.time_now(), 'message_type': Config.CLIENT_INIT_MESSAGE, 'session_id': self._session_id, 'client_id': self._client_id}
        headers = self._create_headers(message_type= Config.CLIENT_INIT_MESSAGE)
        message = Message(headers= headers, content= client_init_message.to_dict()).to_json()
        self._queue_producer.send_data(message)



    def _start_consumer(self):
        self._queue_consumer.start()

    def _start_training_thread(self):
        LOGGER.info("Start training thread.")
        training_thread = threading.Thread(
            target=self._train,
            name="client_training_thread")
        training_thread.daemon = True
        self._is_training = True
        training_thread.start()


    def _handle_server_init_response(self, msg_received):
        # message_utils.print_message(msg_received)
        message_utils.print_message(msg_received)
        # LOGGER.info(msg_received)

        content = msg_received['content']
        server_init_response: ResponseToInit = ResponseToInit(**content)

        if server_init_response.reconnect:
        # if content['reconnect'] is True:
            LOGGER.info("Reconnect to server.")

        # self._session_id = content['session_id']
        self._session_id = server_init_response.session_id

        self._global_model_name = server_init_response.model_info.global_model_name
        self._received_global_version = server_init_response.model_info.model_version

        # get the exchange condition from server
        self._min_acc = server_init_response.exchange_at.performance
        self._min_epoch = server_init_response.exchange_at.epoch


        # connect to cloud storage service provided by server
        storage_info: StorageInfo = server_init_response.storage_info
        self._cloud_storage_type = storage_info.storage_type

        if self._cloud_storage_type == "s3":
            self._storage_connector = ClientStorageAWS(storage_info)
        else:
            self._storage_connector = ClientStorageMinio(storage_info, parent=None)

        self._is_connected = True

        # Check for new global model version.
        if self._current_global_version < self._received_global_version:
            self._current_global_version = self._received_global_version
            LOGGER.info("Detect new global version.")
            local_path = f"{Config.TMP_GLOBAL_MODEL_FOLDER}{self._global_model_name}"

            while True:
                if self._storage_connector.download(remote_file_path=server_init_response.model_info.model_url, 
                                                local_file_path=local_path):
                    break
                LOGGER.info("Download model failed. Retry in 5 seconds.")
                sleep(5)

        # update info in profile file
        self._update_profile()

        if self._role == "train":
            self._start_training_thread()

        # for testing, do not need to start thread
        # because tester just test whenever it receive new model 
        elif self._role == "test":
            self._test()



    def _handle_server_notify_message(self, msg_received):

        content = msg_received['content']
        server_model_udpate: ServerModelUpdate = ServerModelUpdate(**msg_received['content'])

        with lock:
            # ----- receive and load global message ----
            self._global_chosen_list = server_model_udpate.chosen_id

            # update latest model info
            self._global_model_name = server_model_udpate.global_model_name
            self._received_global_version = server_model_udpate.global_model_version

            # global info for merging process
            self._global_model_update_data_size = server_model_udpate.global_model_update_data_size
            self._global_avg_loss = server_model_udpate.avg_loss
            self._global_avg_qod = server_model_udpate.avg_qod

            LOGGER.info("*" * 20)
            LOGGER.info(
                f"Global data_size, global avg loss, global avg qod: {self._global_model_update_data_size}, {self._global_avg_loss}, {self._global_avg_qod}")
            LOGGER.info("*" * 20)

            # save the previous local version of the global model to log it to file
            self._previous_global_version = self._current_global_version
            # update local version (the latest global model that the client have)
            self._current_global_version = self._received_global_version

            remote_path = f'global-models/{content["model_id"]}_v{self._current_global_version}.pkl'
            local_path = f'{Config.TMP_GLOBAL_MODEL_FOLDER}{content["model_id"]}_v{self._current_global_version}.pkl'


            LOGGER.info("Downloading new global model............")

            while True:
                if self._storage_connector.download(remote_file_path=remote_path,
                                                    local_file_path=local_path):
                    break
                LOGGER.info("Download model failed. Retry in 5 seconds.")
                sleep(5)

            LOGGER.info(f"Successfully downloaded new global model, version {self._current_global_version}")
            self._new_model_flag = True
            # print the content only when succesfully download new model
            message_utils.print_message(msg_received)
            

        # test everytime receive new global model notify from server
        if self._role == "test":
            self._test()

    # queue handling functions
    def _handle_server_ping_to_client(self, msg_received):
        if msg_received['content']['client_id'] == self._client_id:
            message_utils.print_message(msg_received)
            headers = self._create_headers(message_type= Config.CLIENT_PING_MESSAGE)
            message = Message(headers= headers, content=ResponseToPing().to_dict()).to_json()
            self._queue_producer.send_data(message)


    def _create_headers(self, message_type: str) -> dict:
        headers = {'timestamp': time_utils.time_now(), 'message_type': message_type, 'session_id': self._session_id, 'client_id': self._client_id}
        return headers

    # profile related
    def _create_message(self):
        data = {
            "session_id": self._session_id,
            "client_id": self._client_id,
            "global_model_name": self._global_model_name,
            "local_epoch": self._local_epoch - 1,
            "local_qod": self._local_qod,
            "save_global_model_version": self._current_global_version,
            "save_global_model_update_data_size": self._global_model_update_data_size,
            "save_global_avg_loss": self._global_avg_loss,
            "save_global_avg_qod": self._global_avg_qod,
        }
        return data

    def _create_profile(self):
        data = self._create_message()
        with open("profile.json", "w") as outfile:
            json.dump(data, outfile)

    def _update_profile(self):
        data = self._create_message()
        with open("profile.json", "w") as outfile:
            json.dump(data, outfile)

    # load client information from profile.json function
    def _load_profile(self):
        try:
            with open("profile.json") as json_file:
                data = json.load(json_file)
                self._session_id = data["session_id"]
                self._client_id = data["client_id"]
                self._global_model_name = data["global_model_name"]
                self._local_epoch = data["local_epoch"]
                self._local_qod = data["local_qod"]

                self._save_global_model_version = data["save_global_model_version"]
                self._save_global_model_update_data_size = data["save_global_model_update_data_size"]
                self._save_global_avg_loss = data["save_global_avg_loss"]
                self._save_global_avg_qod = data["save_global_avg_qod"]


        except Exception as e:
            LOGGER.info(e)

