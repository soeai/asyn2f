import os
import json
import logging
import threading
import uuid
from abc import abstractmethod
from .client_storage_connector import ClientStorage
from asynfed.commons.conf import RoutingRules, Config, init_config
from asynfed.commons.messages.client_init_connect_to_server import ClientInit, SysInfo, DataDesc, QoD
from asynfed.commons.messages import ServerInitResponseToClient
from asynfed.commons.messages import ServerNotifyModelToClient
from asynfed.commons.utils import QueueConnector

LOGGER = logging.getLogger(__name__)

lock = threading.Lock()


class Client(QueueConnector):
    def __init__(self):
        super().__init__()

        # Dependencies
        self._local_data_size = 0

        self._previous_local_version = 0
        self._current_local_version = -1

        self._global_model_version = None

        self._local_epoch = 0

        self._global_avg_loss = None
        self._global_model_update_data_size = None
        self._global_model_name = None
        self._storage_connector = None

        # variables.
        self._client_id = ""
        self._is_training = False
        self._session_id = ""
        self._client_identifier = str(uuid.uuid4())
        self._new_model_flag = False
        self._is_registered = False

        # if there is no profile.json file, then create a new one.
        if not os.path.exists("profile.json"):
            self.create_profile()
        else:
            self.load_profile()

        self.log: bool = True
        init_config("client")


    @abstractmethod
    def train(self):
        pass

    def create_profile(self):
        data = {
            "session_id": self._session_id,
            "client_id": self._client_id,
            "local_data_size": self._local_data_size,
            "global_model_name": self._global_model_name,
            "global_model_version": self._global_model_version,
            "local_epoch": self._local_epoch,
            "global_avg_loss": self._global_avg_loss,
            "global_model_update_data_size": self._global_model_update_data_size,
        }
        with open("profile.json", "w") as outfile:
            json.dump(data, outfile)

    def update_profile(self):
        data = {
            "session_id": self._session_id,
            "client_id": self._client_id,
            "local_data_size": self._local_data_size,
            "global_model_name": self._global_model_name,
            "global_model_version": self._global_model_version,
            "local_epoch": self._local_epoch,
            "global_avg_loss": self._global_avg_loss,
            "global_model_update_data_size": self._global_model_update_data_size,
        }
        with open("profile.json", "w") as outfile:
            json.dump(data, outfile)

    # load client information from profile.json function
    def load_profile(self):
        try:
            with open("profile.json") as json_file:
                data = json.load(json_file)
                self._session_id = data["session_id"]
                self._client_id = data["client_id"]
                self._local_data_size = data["local_data_size"]
                self._global_model_name = data["global_model_name"]
                self._global_model_version = data["global_model_version"]
                self._local_epoch = data["local_epoch"]
                self._global_avg_loss = data["global_avg_loss"]
                self._global_model_update_data_size = data["global_model_update_data_size"]
        except Exception as e:
            print(e)

    # Run the client
    def run(self):
        self.run_queue()

    def setup(self):
        # declare queue
        self._channel.queue_declare(queue=Config.QUEUE_NAME)

        # binding.
        self._channel.queue_bind(
            Config.QUEUE_NAME,
            Config.TRAINING_EXCHANGE,
            RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT,
        )

        self._channel.queue_bind(
            Config.QUEUE_NAME,
            Config.TRAINING_EXCHANGE,
            RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT,
        )
        self.publish_init_message()
        self.start_consuming()

    def on_message(self, channel, basic_deliver, properties, body):
        # If message come from routing SERVER_INIT_RESPONSE_TO_CLIENT then save the model id.
        if basic_deliver.routing_key == RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT:
            message = ServerInitResponseToClient()
            decoded = json.loads(bytes.decode(body))
            message.deserialize(decoded)

            LOGGER.info(message.__dict__)

            # Get only the message that server reply to it base on the session_id
            if self._client_identifier == message.client_identifier:
                # set client property from message
                if self._session_id == message.session_id:
                    # welcome back message
                    LOGGER.info(
                        f"Welcome back {message.client_id} | session_id: {message.session_id}"
                    )
                else:
                    # registration message
                    LOGGER.info(
                        f"Client {message.client_id} is succesfully registered | session_id: {message.session_id}"
                    )
                self._session_id = message.session_id
                self._client_id = message.client_id
                self._global_model_name = message.model_url
                self._global_model_version = message.model_version

                LOGGER.info(
                    f'Init connection to the server successfully | access_key: {message.access_key} | secret_key: {message.secret_key} | model_url: {message.model_url}')
                Config.STORAGE_ACCESS_KEY = message.access_key
                Config.STORAGE_SECRET_KEY = message.secret_key
                Config.STORAGE_REGION_NAME = message.region_name
                Config.STORAGE_BUCKET_NAME = message.bucket_name
                Config.TRAINING_EXCHANGE = message.training_exchange
                Config.QUEUE_NAME = self._client_id
                Config.MONITOR_QUEUE = message.monitor_queue

                self._storage_connector = ClientStorage()

                LOGGER.info(
                    f"Init connection to the server successfully | access_key: {message.access_key} | secret_key: {message.secret_key} | model_url: {message.model_url}"
                )
                self._is_registered = True

                # if local model version is smaller than the global model version and client's id is in the chosen ids
                if self._current_local_version < self._global_model_version:
                    LOGGER.info("Detect new global version.")

                    filename = self._global_model_name.split("/")[-1]
                    local_path = f"{Config.TMP_GLOBAL_MODEL_FOLDER}{filename}"

                    while True:
                        if self._storage_connector.download(
                                bucket_name=Config.STORAGE_BUCKET_NAME,
                                remote_file_path=self._global_model_name,
                                local_file_path=local_path,
                        ):
                            break

                    # start 1 thread to train model.
                    self.start_training_thread()

        elif (
                basic_deliver.routing_key == RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT
                and self._is_registered
        ):
            # download model.
            decoded = json.loads(bytes.decode(body))
            msg = ServerNotifyModelToClient()
            msg.deserialize(decoded)

            LOGGER.info("Receive global model notify.")

            with lock:
                self._global_model_name = msg.global_model_name

                self._global_model_version = msg.global_model_version

                # save the previous local version of the global model to log it to file
                self._previous_local_version = self._current_local_version
                # update local version (the latest global model that the client have)

                self._current_local_version = self._global_model_version
                self._global_model_update_data_size = msg.global_model_update_data_size
                self._global_avg_loss = msg.avg_loss

                # if local model version is smaller than the global model version and client's id is in the chosen ids
                if self._current_local_version < self._global_model_version:
                    LOGGER.info("Detect new global version.")

                    remote_path = f'global-models/{msg.model_id}_v{msg.global_model_version}.pkl'
                    local_path = f'{Config.TMP_GLOBAL_MODEL_FOLDER}{msg.model_id}_v{msg.global_model_version}.pkl'

                    while True:
                        if self._storage_connector.download(bucket_name=Config.STORAGE_BUCKET_NAME,
                                                            remote_file_path=remote_path,
                                                            local_file_path=local_path):
                            break

                # change the flag to true.
                self._new_model_flag = True

    def notify_model_to_server(self, message):
        self._channel.basic_publish(
            Config.TRAINING_EXCHANGE,
            RoutingRules.CLIENT_NOTIFY_MODEL_TO_SERVER,
            message
        )

    def init_connect_to_server(self, message):
        self._channel.basic_publish(
            Config.TRAINING_EXCHANGE,
            RoutingRules.CLIENT_INIT_SEND_TO_SERVER,
            message
        )


    def publish_init_message(self):
        message = ClientInit(
            client_identifier=self._client_identifier,
            session_id=self._session_id,
            client_id=self._client_id,
            sys_info=SysInfo(),
            data_desc=DataDesc(),
            qod=QoD(),
        )
        self.init_connect_to_server(message.serialize())

    def start_training_thread(self):
        if not self._is_training:
            LOGGER.info("Start training thread.")
            training_thread = threading.Thread(
                target=self.train,
                name="client_training_thread")

            self._is_training = True
            training_thread.start()
