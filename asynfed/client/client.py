import os, sys
from asynfed.client.messages.ping import Ping
from asynfed.commons.utils.time_ultils import time_now
root = os.path.dirname(os.path.dirname(os.getcwd()))
sys.path.append(root)

import json
import logging
import os
import threading
import uuid
from time import sleep

from abc import abstractmethod
from asynfed.client.client_storage_connector import ClientStorageAWS,ClientStorageMinio

from asynfed.client.messages import InitConnection
from asynfed.commons.conf import Config, init_config

from asynfed.commons.messages import MessageV2
from asynfed.commons.utils import AmqpConsumer
from asynfed.commons.utils import AmqpProducer

from .ModelWrapper import ModelWrapper
import concurrent.futures
thread_pool_ref = concurrent.futures.ThreadPoolExecutor


LOGGER = logging.getLogger(__name__)
logging.getLogger('pika').setLevel(logging.WARNING)
LOGGER.setLevel(logging.INFO)

lock = threading.Lock()


class Client(object):
    def __init__(self, model: ModelWrapper, config, save_log=False):
        self.config = config
        self._role = config.get("role") or "train"
        self._ping_time = config.get("ping_time") or 30

        if self._role == "train":
            self._min_epoch = config['training_params']['min_epoch']
            self._min_acc = config['training_params']['min_acc']
        
        self._is_stop_condition = False
        # Dependencies
        self._global_chosen_list = None
        self._save_global_avg_qod = None
        self._save_global_avg_loss = None
        self._save_global_model_update_data_size = None
        self._save_global_model_version = None

        self.model = model
        self._local_data_size = self.model.data_size
        self._local_qod = self.model.qod
        self._train_acc = 0.0
        self._train_loss = 0.0

        # for updating new global model
        self._previous_global_version = 0
        self._current_global_version = 0
        self._received_global_version = 0

        self._global_model_name = None

        self._local_epoch = 0

        # merging process
        self._global_avg_loss = None
        self._global_avg_qod = None
        self._global_model_update_data_size = None

        # variables.
        if self.config['client_id'] is None:
            self._client_id = str(uuid.uuid4())
        else:
            self._client_id = self.config['client_id']
        self._is_training = False
        self._session_id = ""
        self._new_model_flag = False
        self._is_connected = False

        self.config['queue_consumer']['queue_name'] = "queue_" + self._client_id

        # Initialize profile for client
        if not os.path.exists("profile.json"):
            self.create_profile()
        else:
            self.load_profile()


        init_config("client", save_log)

        self.thread_consumer = threading.Thread(target=self._start_consumer)
        self.queue_consumer = AmqpConsumer(self.config['queue_consumer'], self)
        self.queue_producer = AmqpProducer(self.config['queue_producer'])

        LOGGER.info(f'\n\nClient Id: {self._client_id}'
                    f'\n\tQueue In : {self.config["queue_consumer"]}'
                    f'\n\tQueue Out : {self.config["queue_producer"]}'
                    f'\n\n')

        self._send_init_message()

    def on_download(self, result):
        if result:
            self._new_model_flag = True
            LOGGER.info(f"Successfully downloaded new global model, version {self._global_model_version}")
        else:
            LOGGER.info("Download model failed. Passed this version!")

    def on_upload(self, result):
        pass

    def on_message_received(self, ch, method, props, body):
        msg_received = MessageV2.deserialize(body.decode('utf-8'))

        if msg_received['headers']['message_type'] == Config.SERVER_INIT_RESPONSE and not self._is_connected:
            self._handle_server_init_response(msg_received)
        elif msg_received['headers']['message_type'] == Config.SERVER_NOTIFY_MESSAGE and self._is_connected:
            self._handle_server_notify_message(msg_received)
        elif msg_received['headers']['message_type'] == Config.SERVER_STOP_TRAINING: 
            MessageV2.print_message(msg_received)
            self._is_stop_condition = True
            sys.exit(0)
        elif msg_received['headers']['message_type'] == Config.SERVER_PING_TO_CLIENT:
            self._handle_server_ping_to_client(msg_received)

    def _handle_server_ping_to_client(self, msg_received):
        if msg_received['content']['client_id'] == self._client_id:
            MessageV2.print_message(msg_received)
            message = MessageV2(
                    headers={"timestamp": time_now(), "message_type": Config.CLIENT_PING_MESSAGE, "session_id": self._session_id, "client_id": self._client_id},
                    content=Ping()).to_json()
            self.queue_producer.send_data(message)

    @abstractmethod
    def train(self):
        pass

    def create_message(self):
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

            # "local_data_size": self._local_data_size,
            # "local_qod": self._local_qod,
            # "train_loss": self._train_loss,
        }
        return data

    def create_profile(self):
        data = self.create_message()
        with open("profile.json", "w") as outfile:
            json.dump(data, outfile)

    def update_profile(self):
        data = self.create_message()
        with open("profile.json", "w") as outfile:
            json.dump(data, outfile)

    # load client information from profile.json function
    def load_profile(self):
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

                # self._local_data_size = data["local_data_size"]
                # self._train_loss = data["train_loss"]
        except Exception as e:
            LOGGER.info(e)

    def _send_init_message(self):
        data_description = {
            'data_size': self._local_data_size,
            'qod': self._local_qod,
        }
        message = MessageV2(
            headers={'timestamp': time_now(), 'message_type': Config.CLIENT_INIT_MESSAGE, 'session_id': self._session_id, 'client_id': self._client_id},
            content=InitConnection(
                role=self._role,
                data_description=data_description,
            )
        ).to_json()
        self.queue_producer.send_data(message)

    def _handle_server_init_response(self, msg_received):
        MessageV2.print_message(msg_received)

        content = msg_received['content']
        if content['reconnect'] is True:
            LOGGER.info("Reconnect to server.")

        self._session_id = content['session_id']
        self._global_model_name = content['model_info']['global_model_name']
        self._received_global_version = content['model_info']['model_version']
        # self._storage_connector = ClientStorageAWS(content['aws_info'])
        self._storage_connector = ClientStorageMinio(content['minio_info'])
        self._is_connected = True

        # Check for new global model version.
        if self._current_global_version < self._received_global_version:
            self._current_global_version = self._received_global_version
            LOGGER.info("Detect new global version.")
            local_path = f"{Config.TMP_GLOBAL_MODEL_FOLDER}{self._global_model_name}"

            while True:
                if self._storage_connector.download(remote_file_path=content['model_info']['model_url'], 
                                                local_file_path=local_path):
                    break
                LOGGER.info("Download model failed. Retry in 5 seconds.")
                sleep(5)

        self.update_profile()
        if self._role == "train":
            self.start_training_thread()
        elif self._role == "test":
            self.start_testing_thread()

    def _handle_server_notify_message(self, msg_received):
        content = msg_received['content']
        MessageV2.print_message(msg_received)
        with lock:
            # ----- receive and load global message ----
            self._global_chosen_list = content['chosen_id']

            # update latest model info
            self._global_model_name = content['global_model_name']
            self._received_global_version = content['global_model_version']

            # global info for merging process
            self._global_model_update_data_size = content['global_model_update_data_size']
            self._global_avg_loss = content['avg_loss']
            self._global_avg_qod = content['avg_qod']
            LOGGER.info("*" * 20)
            LOGGER.info(
                f"global data_size, global avg loss, global avg qod: {self._global_model_update_data_size}, {self._global_avg_loss}, {self._global_avg_qod}")
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

        if self._role == "test":
            self._test()

    @abstractmethod
    def _test(self):
        pass

    def _start_consumer(self):
        self.queue_consumer.start()

    # Run the client
    def start(self):
        self.thread_consumer.start()

        # Main thread will send ping message to server every t seconds
        while not self._is_stop_condition:
            sleep(30)

        sys.exit(0)

    def start_training_thread(self):
        LOGGER.info("Start training thread.")
        training_thread = threading.Thread(
            target=self.train,
            name="client_training_thread")
        training_thread.daemon = True
        self._is_training = True
        training_thread.start()

    def start_testing_thread(self):
        LOGGER.info("Start testing thread.")
        testing_thread = threading.Thread(
            target=self._test,
            name="client_testing_thread")
        testing_thread.daemon = True
        self._is_testing = True
        testing_thread.start()

