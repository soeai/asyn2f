import json
import logging
import threading
import uuid

from fedasync.client.client_storage_connector import ClientStorage
from fedasync.client.model import ClientModel
from fedasync.commons.conf import Config, RoutingRules, StorageConfig
from fedasync.commons.messages.client_init_connect_to_server import ClientInit
from fedasync.commons.messages.server_init_response_to_client import ServerInitResponseToClient
from fedasync.commons.messages.server_notify_model_to_client import ServerNotifyModelToClient
from fedasync.commons.utils.queue_connector import QueueConnector

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

lock = threading.Lock()


class ClientQueueConnector(QueueConnector):
    def __init__(self, client_model: ClientModel):
        super().__init__()

        # Dependencies
        self.client_model: ClientModel = client_model
        self.storage_connector: ClientStorage = None

        # variables.
        self.client_id = ""
        self.is_training = False
        self.session_id = uuid.uuid4()

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

        # send registration message
        message = ClientInit()
        message.session_id = self.session_id

        self.init_connect_to_server(
            # Send a message to server to init connection
            message.serialize()
        )

        self.start_consuming()

    def on_message(self, channel, basic_deliver, properties, body):

        # if message come from routing SERVER_INIT_RESPONSE_TO_CLIENT then save the model id.
        if basic_deliver.routing_key == RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT:
            decoded = json.loads(bytes.decode(body))
            message = ServerInitResponseToClient(decoded)

            # get only the message that server reply to it base on the session_id
            if self.session_id == message.session_id:
                # set client property from message
                self.client_id = message.client_id
                self.client_id.global_model_name = message.model_url

                LOGGER.info(
                    f'Init connection to the server successfully | access_key: {message.access_key} | secret_key: {message.secret_key} | model_url: {message.model_url}')
                StorageConfig.ACCESS_KEY = message.access_key
                StorageConfig.SECRET_KEY = message.secret_key

                self.storage_connector = ClientStorage(self.client_id)

                # set client storage connector.
                self.client_model._storage_connector = self.storage_connector

                # download model.
                self.storage_connector.get_model(self.client_model.global_model_name)
                self.client_model.__new_model_flag = True

        elif basic_deliver.routing_key == RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT:
            # download model.
            decoded = json.loads(bytes.decode(body))
            msg = ServerNotifyModelToClient(decoded)

            LOGGER.info("Receive global model notify.")

            with lock:
                self.client_model.global_model_name = msg.global_model_name
                self.client_model.global_model_version = msg.global_model_version
                self.client_model.global_model_update_data_size = msg.global_model_update_data_size
                self.client_model.global_avg_loss = msg.avg_loss

                # if local model version is smaller than the global model version and client's id is in the chosen ids
                if self.client_model.local_version < msg.global_model_version and (
                        len(msg.chosen_id) == 0 or self.client_id in msg.chosen_id):

                    # download model
                    self.storage_connector.get_model(self.client_model.global_model_name)

                    # change the flag to true.
                    self.client_model.__new_model_flag = True

                    # start 1 thread to train model.
                    if not self.is_training:
                        training_thread = threading.Thread(
                            target=self.client_model.train,
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
