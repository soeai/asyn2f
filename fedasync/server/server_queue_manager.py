from pika import BasicProperties

from fedasync.commons.messages.client_init_connect_to_server import ClientInit
from fedasync.commons.messages.client_notify_model_to_server import ClientNotifyModelToServer
from fedasync.commons.utils.consumer import Consumer
from fedasync.commons.utils.producer import Producer
import logging
from fedasync.commons.conf import Config, RoutingRules
from fedasync.commons.utils import CloudStorageConnector

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class ServerConsumer(Consumer):
    def __init__(self, cloud_storage: CloudStorageConnector):
        super().__init__()
        self.cloud_storage: CloudStorageConnector = cloud_storage

    def on_message(self, channel, method, properties: BasicProperties, body):

        if method.routing_key == RoutingRules.CLIENT_INIT_SEND_TO_SERVER:
            # get message and convert it
            message = ClientInit(body.decode())

            # create worker and add worker to manager.

            # if number of worker > 1 then publish global model.

            pass
        elif method.routing_key == RoutingRules.CLIENT_NOTIFY_MODEL_TO_SERVER:
            # download local model.
            message = ClientNotifyModelToServer(body.decode())
            self.cloud_storage.download(message.link)

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
