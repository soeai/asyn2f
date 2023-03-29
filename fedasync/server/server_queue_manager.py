import json
import uuid

from pika import BasicProperties

from fedasync.commons.messages.client_init_connect_to_server import ClientInit
from fedasync.commons.messages.client_notify_model_to_server import ClientNotifyModelToServer
from fedasync.commons.messages.server_init_response_to_client import ServerInitResponseToClient
from fedasync.commons.utils.cloud_storage_connector import MinioConnector
from fedasync.commons.utils.consumer import Consumer
from fedasync.commons.utils.producer import Producer
import logging
from fedasync.commons.conf import Config, RoutingRules
from fedasync.commons.utils import CloudStorageConnector
from fedasync.server.objects import Worker
from fedasync.server.worker_manager import WorkerManager

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class ServerConsumer(Consumer):
    def __init__(self, cloud_storage: CloudStorageConnector = None, worker_manager: WorkerManager = None):
        super().__init__()
        self.cloud_storage: CloudStorageConnector = cloud_storage
        self.worker_manager: WorkerManager = worker_manager

    def on_message(self, channel, method, properties: BasicProperties, body):

        if method.routing_key == RoutingRules.CLIENT_INIT_SEND_TO_SERVER:
            # get message and convert it
            client_init_message: ClientInit = ClientInit(body.decode())
            print(client_init_message.serialize())

            # create worker and add worker to manager.
            new_id = str(uuid.uuid4())
            new_worker = Worker(new_id)
            new_worker.qod = client_init_message.qod
            new_worker.sys_info = client_init_message.sys_info
            new_worker.data_desc = client_init_message.data_desc

            # if number of worker > 1 then publish it's model.

            response = ServerInitResponseToClient()
            response.session_id = client_init_message.sessionid
            response.client_id = new_worker.id

            # minio_keys =
            response.access_key = ""
            response.secret_key = ""

            self._channel.basic_publish(
                Config.TRAINING_EXCHANGE,
                routing_key=RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT,
                body=response.serialize()
            )

        elif method.routing_key == RoutingRules.CLIENT_NOTIFY_MODEL_TO_SERVER:
            # download local model.
            client_noty_message = ClientNotifyModelToServer(body.decode())
            self.cloud_storage.download(f'{client_noty_message.client_id}/{client_noty_message.link}')
            LOGGER.info("New model downloaded download ")
        LOGGER.info(method.routing_key)
        LOGGER.info(body)

    def setup(self):
        # declare exchange.
        self._channel.exchange_declare(exchange=Config.TRAINING_EXCHANGE, exchange_type=self.EXCHANGE_TYPE)

        # declare queue
        self._channel.queue_declare(queue=Config.QUEUE_NAME)

        # binding.
        self._channel.queue_bind(
            Config.QUEUE_NAME,
            Config.TRAINING_EXCHANGE,
            RoutingRules.CLIENT_NOTIFY_MODEL_TO_SERVER
        )

        self._channel.queue_bind(
            Config.QUEUE_NAME,
            Config.TRAINING_EXCHANGE,
            RoutingRules.CLIENT_INIT_SEND_TO_SERVER
        )

        self.start_consuming()


class ServerProducer(Producer):
    def __init__(self):
        super().__init__()

    def notify_global_model_to_client(self, message):
        self.publish_message(
            RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT,
            message
        )

    def response_to_client_init_connect(self, message):
        self.publish_message(
            RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT,
            message
        )
