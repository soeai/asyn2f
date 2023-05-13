import json
import logging
import threading
import uuid
from abc import abstractmethod
from fedasync.client.client_storage_connector import ClientStorage
from fedasync.commons.conf import GlobalConfig, RoutingRules, StorageConfig
from fedasync.commons.messages.client_init_connect_to_server import ClientInit, SysInfo, DataDesc, QoD
from fedasync.commons.messages.server_init_response_to_client import ServerInitResponseToClient
from fedasync.commons.messages.server_notify_model_to_client import ServerNotifyModelToClient
from fedasync.commons.utils.queue_connector import QueueConnector

import time

# Define logger
LOG_FORMAT = '%(levelname) -10s %(asctime)s %(name) -30s %(funcName) -35s %(lineno) -5d: %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    filename="./logs/worker_log.txt",
    filemode='a',
    datefmt='%H:%M:%S'
)
LOGGER = logging.getLogger(__name__)


lock = threading.Lock()


# ClientConfig.QUEUE_NAME = 'client_queue'

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
        self._session_id = str(uuid.uuid4())
        self._new_model_flag = False
        self._is_registered = False

    # Run the client
    def run(self):
        self.run_queue()

    def setup(self):

        # declare queue
        self._channel.queue_declare(queue=GlobalConfig.QUEUE_NAME)

        # binding.
        self._channel.queue_bind(
            GlobalConfig.QUEUE_NAME,
            GlobalConfig.TRAINING_EXCHANGE,
            RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT
        )

        self._channel.queue_bind(
            GlobalConfig.QUEUE_NAME,
            GlobalConfig.TRAINING_EXCHANGE,
            RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT
        )
        self.publish_init_message()
        self.start_consuming()

    def on_message(self, channel, basic_deliver, properties, body):
        # If message come from routing SERVER_INIT_RESPONSE_TO_CLIENT then save the model id.
        if basic_deliver.routing_key == RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT:
            message = ServerInitResponseToClient()
            decoded = json.loads(bytes.decode(body))
            message.deserialize(decoded)

            # Get only the message that server reply to it base on the session_id
            if self._session_id == message.session_id:
                # set client property from message
                self._client_id = message.client_id
                self._global_model_name = message.model_url
                self._global_model_version = message.model_version
                self._access_key_id = message.access_key

                LOGGER.info(
                    f'Init connection to the server successfully | access_key: {message.access_key} | secret_key: {message.secret_key} | model_url: {message.model_url}')
                StorageConfig.ACCESS_KEY = message.access_key
                StorageConfig.SECRET_KEY = message.secret_key

                self._storage_connector = ClientStorage()
                # sleep(5)
                self._is_registered = True
                # if local model version is smaller than the global model version and client's id is in the chosen ids
                if self._current_local_version < self._global_model_version:
                    LOGGER.info("Detect new global version.")

                    filename = self._global_model_name.split('/')[-1]
                    local_path = f'{GlobalConfig.TMP_GLOBAL_MODEL_FOLDER}{filename}'

                    while True:
                        time.sleep(5)
                        import os
                        LOGGER.info(os.getcwd())
                        if self._storage_connector.download(StorageConfig.BUCKET_NAME, self._global_model_name, local_path):
                            break

                    # start 1 thread to train model.
                    self.start_training_thread()

        elif basic_deliver.routing_key == RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT and self._is_registered:
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

                remote_path = f'global-models/{msg.model_id}_v{msg.global_model_version}.pkl'
                local_path = f'{GlobalConfig.TMP_GLOBAL_MODEL_FOLDER}{msg.model_id}_v{msg.global_model_version}.pkl'
                LOGGER.info("*" * 10)
                LOGGER.info(remote_path)
                LOGGER.info(local_path)
                LOGGER.info("*" * 10)

                self._storage_connector.download(bucket_name=StorageConfig.BUCKET_NAME, remote_file_path=remote_path,
                                                 local_file_path=local_path)

                # change the flag to true.
                self._new_model_flag = True

    def notify_model_to_server(self, message):
        self._channel.basic_publish(
            GlobalConfig.TRAINING_EXCHANGE,
            RoutingRules.CLIENT_NOTIFY_MODEL_TO_SERVER,
            message
        )

    def init_connect_to_server(self, message):
        self._channel.basic_publish(
            GlobalConfig.TRAINING_EXCHANGE,
            RoutingRules.CLIENT_INIT_SEND_TO_SERVER,
            message
        )

        # Abstract methods

    @abstractmethod
    def set_weights(self, weights):
        pass

    @abstractmethod
    def get_weights(self):
        pass

    @abstractmethod
    def train(self):
        pass

    @abstractmethod
    def evaluate(self, test_dataset):
        pass

    def publish_init_message(self):
        message = ClientInit(
            session_id=self._session_id,
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
