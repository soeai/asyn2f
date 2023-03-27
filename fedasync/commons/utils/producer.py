
import logging
from abc import ABC

import pika

from fedasync.commons.conf import Config

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class Producer(ABC):

    def __init__(self):
        LOGGER.info('Connecting to %s', Config.QUEUE_URL)
        self._connection = pika.BlockingConnection(pika.URLParameters(Config.QUEUE_URL))
        self._channel = self._connection.channel()

    def publish_message(self, routing_key, message):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.

        :rtype: pika.SelectConnection

        """
        self._channel.basic_publish(
            Config.TRAINING_EXCHANGE,
            routing_key,
            message
        )

        self._channel.close()
        self._connection.close()



