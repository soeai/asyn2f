from abc import abstractmethod
import pika
import logging

from pika import BlockingConnection
from pika.adapters.blocking_connection import BlockingChannel
from pika.channel import Channel
from pika.exchange_type import ExchangeType
from pika.spec import Basic, BasicProperties

from asynfed.commons import Config

LOGGER = logging.getLogger(__name__)


class BlockingQueueConnector:
    def __init__(self):
        self._channel: BlockingChannel = None
        self._connection: BlockingConnection = None

    def _reconnect(self):
        self._connect()

    def run_queue(self):

        # connect to queue server and create queue
        self.setup()

        method_frame: Basic.GetOk
        header_frame: BasicProperties

        # Enter EventLoop.
        while True:
            try:
                if self._connection is None or self._channel is None:
                    self._reconnect()
                else:
                    method_frame, header_frame, body = self._channel.basic_get(Config.QUEUE_NAME)

                    if method_frame:
                        self._channel.basic_ack(method_frame.delivery_tag)

                        self.on_message(method_frame, header_frame, body)

            except Exception as error:
                print(error)
                print("Trying to reconnect...")

    def stop(self):
        self._close_connection()
        return

    def _connect(self):
        while True:
            try:
                self._connection = pika.BlockingConnection(pika.URLParameters(Config.QUEUE_URL))
                if self._connection is not None:
                    break
            except Exception as error:
                print(error)

    def _close_connection(self):
        self._channel.close()
        self._connection.close()

    @abstractmethod
    def setup(self):
        """
        Setup Queue for consumer.
        """

    @abstractmethod
    def on_message(self, method, properties, body):
        pass

