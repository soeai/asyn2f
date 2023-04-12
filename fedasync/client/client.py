import json
import logging
import threading
import uuid
from abc import abstractmethod
from fedasync.client.client_storage_connector import ClientStorage
from fedasync.commons.conf import Config, RoutingRules, StorageConfig
from fedasync.commons.messages.client_init_connect_to_server import ClientInit, SysInfo, DataDesc, QoD
from fedasync.commons.messages.server_init_response_to_client import ServerInitResponseToClient
from fedasync.commons.messages.server_notify_model_to_client import ServerNotifyModelToClient
from fedasync.commons.utils.queue_connector import QueueConnector

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

lock = threading.Lock()


# Config.QUEUE_NAME = 'client_queue'

class Client(QueueConnector):
    def __init__(self):
        super().__init__()

        # Dependencies
        self.local_version = 0
        self.global_avg_loss = None
        self.global_model_update_data_size = None
        self.global_model_version = None
        self.global_model_name = None
        self.storage_connector: ClientStorage = None

        # variables.
        self.client_id = ""
        self.is_training = False
        self.session_id = str(uuid.uuid4())
        self._new_model_flag = False
        self._is_registered = False

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
            RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT
        )

        self._channel.queue_bind(
            Config.QUEUE_NAME,
            Config.TRAINING_EXCHANGE,
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
            if self.session_id == message.session_id:
                # set client property from message
                self.client_id = message.client_id
                self.global_model_name = message.model_url
                self.global_model_version = message.model_version

                LOGGER.info(
                    f'Init connection to the server successfully | access_key: {message.access_key} | secret_key: {message.secret_key} | model_url: {message.model_url}')
                StorageConfig.ACCESS_KEY = message.access_key
                StorageConfig.SECRET_KEY = message.secret_key

                self.storage_connector = ClientStorage(self.client_id)
                self._is_registered = True
                # if local model version is smaller than the global model version and client's id is in the chosen ids
                if self.local_version < self.global_model_version:
                    LOGGER.info("Found new model.")
                    # download model
                    self.storage_connector.get_model(self.global_model_name)

                    # change the flag to true.
                    self._new_model_flag = True

                    # start 1 thread to train model.
                    if not self.is_training:
                        training_thread = threading.Thread(
                            target=self.train,
                            name="client_training_thread")

                        self.is_training = True
                        training_thread.start()

        elif basic_deliver.routing_key == RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT and self._is_registered:
            # download model.
            decoded = json.loads(bytes.decode(body))
            msg = ServerNotifyModelToClient()
            msg.deserialize(decoded)
            print(msg)

            LOGGER.info("Receive global model notify.")

            with lock:
                self.global_model_name = msg.global_model_name
                self.global_model_version = msg.global_model_version
                self.global_model_update_data_size = msg.global_model_update_data_size
                self.global_avg_loss = msg.avg_loss

                # if local model version is smaller than the global model version and client's id is in the chosen ids
                if self.local_version < msg.global_model_version and (
                        len(msg.chosen_id) == 0 or self.client_id in msg.chosen_id):
                    # download model
                    self.storage_connector.get_model(self.global_model_name)

                    # change the flag to true.
                    self._new_model_flag = True

                    # start 1 thread to train model.
                    if not self.is_training:
                        training_thread = threading.Thread(
                            target=self.train,
                            name="client_training_thread")

                        self.is_training = True
                        training_thread.start()

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
    def evaluate(self):
        pass

    def publish_init_message(self):
        message = ClientInit(
            session_id=self.session_id,
            sys_info=SysInfo(),
            data_desc=DataDesc(),
            qod=QoD(),
        )
        self.init_connect_to_server(message.serialize())
