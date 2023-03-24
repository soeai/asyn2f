import functools
import logging
from abc import ABC, abstractmethod
import pika
from pika.exchange_type import ExchangeType

from fedasync.commons.utils.queue_manager import QueueManager

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class ClientQueueManager(QueueManager):
    def __init__(self):
        super().__init__()

    def setup_queue(self):
        pass

    def setup_exchange(self):
        pass

    def on_message(self, _unused_channel, basic_deliver, properties, body):
        pass

    def on_queue_declareok(self, _unused_frame, userdata):
        pass



