from fedasync.commons.utils.consumer import Consumer
from fedasync.commons.utils.producer import Producer
import logging
from fedasync.commons.conf import Config

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class ServerConsumer(Consumer):
    def __init__(self):
        super().__init__()

    def on_message(self, channel, basic_deliver, properties, body):
        print(body)
        logging.info(body)

    def setup(self):
        # declare exchange.
        self._channel.exchange_declare(exchange=Config.TRAINING_EXCHANGE, exchange_type=self.EXCHANGE_TYPE)

        # declare queue
        self._channel.queue_declare(queue=Config.QUEUE_NAME)

        # binding.
        self._channel.queue_bind(
            Config.QUEUE_NAME,
            Config.TRAINING_EXCHANGE,
            Config.CLIENT_NOTIFY_MODEL_TO_SERVER
        )

        self._channel.queue_bind(
            Config.QUEUE_NAME,
            Config.TRAINING_EXCHANGE,
            Config.CLIENT_INIT_SEND_TO_SERVER
        )

        self.start_consuming()


class ServerProducer(Producer):
    def __init__(self):
        super().__init__()

    def notify_global_model_to_client(self, message):
        self.publish_message(
            Config.SERVER_NOTIFY_MODEL_TO_CLIENT,
            message
        )

    def response_to_client_init_connect(self, message):
        self.publish_message(
            Config.SERVER_INIT_RESPONSE_TO_CLIENT,
            message
        )


