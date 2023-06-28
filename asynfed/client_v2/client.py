import json
import logging
import os
import threading
import uuid
from time import sleep
from abc import abstractmethod
from asynfed.client.client_storage_connector import ClientStorage
from asynfed.commons.conf import RoutingRules
from asynfed.commons.messages import ClientInit
from asynfed.commons.messages.client_init_connect_to_server import SysInfo
from asynfed.commons.utils.queue_consumer import AmqpConsumer
from asynfed.commons.utils.queue_producer import AmqpProducer


LOGGER = logging.getLogger(__name__)

lock = threading.Lock()


class Client(object):
    def __init__(self, config):
        # Dependencies
        self._global_chosen_list = None
        self._save_global_avg_qod = None
        self._save_global_avg_loss = None
        self._save_global_model_update_data_size = None
        self._save_global_model_version = None
        self._local_data_size = 0
        self._local_qod = 0.0
        self._train_loss = 0.0

        self._previous_local_version = 0
        self._current_local_version = 0

        self._global_model_version = None

        self._global_model_name = None
        self._storage_connector = None

        self._local_epoch = 0
        # merging process
        self._global_avg_loss = None
        self._global_avg_qod = None
        self._global_model_update_data_size = None

        # variables.
        self._client_id = ""
        self._is_training = False
        self._session_id = ""
        self._client_identifier = str(uuid.uuid4())
        self._new_model_flag = False
        self._is_registered = False

        # Config.QUEUE_NAME = self._client_identifier

        # if there is no profile.json file, then create a new one.
        if not os.path.exists("profile.json"):
            self.create_profile()
        else:
            self.load_profile()

        self.log: bool = True
        # init_config("client")
        self.thread = threading.Thread(target=self._start_consumer)
        self.queue_concumer = AmqpConsumer(config['queue_consumer'], self)
        self.queue_producer = AmqpProducer(config['queue_producer'])

    def on_message_handling(ch, method, props, body):
        pass

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
            "save_global_model_version": self._global_model_version,
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
            print(e)

    def notify_model_to_server(self, message):
        self.queue_producer.send_data(message)

    def init_connect_to_server(self, message):
        self.queue_producer.send_data(message)

    def publish_init_message(self, data_size=10000, qod=0.2):
        message = ClientInit(
            client_identifier=self._client_identifier,
            session_id=self._session_id,
            client_id=self._client_id,
            sys_info=SysInfo(),
            data_size=data_size,
            qod=qod
        )
        print("-" * 20)
        print("Init message of client")
        print(message)
        print("-" * 20)
        self.init_connect_to_server(message.serialize())

    def _start_consumer(self):
        self.queue_concumer.start()

    # Run the client
    def start_queue(self):
        self.thread.start()

    def start_training_thread(self):
        if not self._is_training:
            LOGGER.info("Start training thread.")
            training_thread = threading.Thread(
                target=self.train,
                name="client_training_thread")

            self._is_training = True
            training_thread.start()
