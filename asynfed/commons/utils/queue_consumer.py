import pika, json, logging

LOGGER = logging.getLogger(__name__)
logging.getLogger('pika').setLevel(logging.WARNING)
LOGGER.setLevel(logging.INFO)

from asynfed.commons.config import QueueConfig


class AmqpConsumer(object):
    def __init__(self, config: QueueConfig, host_object: object = None):
        self._host_object = host_object
        self._config: QueueConfig = config
        self._setup_connection()


    def _setup_connection(self):
        self._connection = pika.BlockingConnection(pika.URLParameters(self._config.endpoint))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(exchange= self._config.queue_exchange, exchange_type= self._config.exchange_type)
        self._queue = self._channel.queue_declare(queue= self._config.queue_name, exclusive= False)
        self._queue_name = self._queue.method.queue
        self._channel.queue_bind(exchange= self._config.queue_exchange, queue= self._queue_name, 
                                 routing_key= self._config.routing_key)


    def on_request(self, ch, method, props, body):
        if self._host_object != None:
            self._host_object.on_message_received(ch, method, props, body)
        else:
            mess = json.loads(str(body.decode("utf-8")))
            LOGGER.info(mess)

    def start(self):
        try:
            self._channel.basic_qos(prefetch_count=1)
            self._channel.basic_consume(queue= self._queue_name, on_message_callback= self.on_request, auto_ack=True)
            self._channel.start_consuming()
            
        except Exception as e:
            LOGGER.info(e)
            LOGGER.exception("Connection lost. Reconnecting...")
            self._reconnect()
            self.start()

    def stop(self):
        self._channel.stop_consuming()
        self._channel.close()

    def get_queue(self):
        return self._queue.method.queue

    def _reconnect(self):
        self._setup_connection()