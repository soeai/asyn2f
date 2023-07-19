import pika, uuid
import logging


LOGGER = logging.getLogger(__name__)
logging.getLogger('pika').setLevel(logging.WARNING)
LOGGER.setLevel(logging.INFO)

from asynfed.commons.config import QueueConfig

class AmqpProducer(object):
    def __init__(self, config: QueueConfig):
        self._config = config
        self._setup_connection()


    def _setup_connection(self):
        self._connection = pika.BlockingConnection(pika.URLParameters(self._config.endpoint))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(exchange= self._config.queue_exchange, exchange_type= self._config.exchange_type)
        self._queue = self._channel.queue_declare(queue= self._config.queue_name, exclusive= False)
        self._queue_name = self._queue.method.queue
        self._channel.queue_bind(exchange=self._config.queue_exchange, queue= self._queue_name, 
                                 routing_key= self._config.routing_key)


    def send_data(self, body_mess, corr_id=None, routing_key= None, expiration= 1000):
        try:
            if not corr_id:
                corr_id = str(uuid.uuid4())
            if not routing_key:
                routing_key = self._config.routing_key
            self.sub_properties = pika.BasicProperties(correlation_id= corr_id, expiration= str(expiration))
            self._channel.basic_publish(exchange= self._config.queue_exchange, routing_key= routing_key,
                                       properties=self.sub_properties, body= body_mess)

        # except pika.exceptions.StreamLostError as e:
        except Exception as e:
            LOGGER.info(e)
            LOGGER.exception("Connection lost. Reconnecting...")
            self._setup_connection()
            self.send_data(body_mess, corr_id, routing_key, expiration)

    def get(self) -> dict:
        return self._config.to_dict()