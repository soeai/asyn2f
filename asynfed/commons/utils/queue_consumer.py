import pika, json, logging

LOGGER = logging.getLogger(__name__)
logging.getLogger('pika').setLevel(logging.WARNING)
LOGGER.setLevel(logging.INFO)

class AmqpConsumer(object):
    def __init__(self, configuration: dict, host_object: object = None):
        self.host_object = host_object
        self.conf = configuration
        self.exchange_name = configuration["exchange_name"]
        self.exchange_type = configuration["exchange_type"]
        self.routing_key = configuration["routing_key"]
        self._setup_connection()

    def _setup_connection(self):
        self.connection = pika.BlockingConnection(pika.URLParameters(self.conf["endpoint"]))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=self.exchange_name, exchange_type=self.exchange_type)
        self.queue = self.channel.queue_declare(queue=self.conf["queue_name"], exclusive=False)
        self.queue_name = self.queue.method.queue
        self.channel.queue_bind(exchange=self.exchange_name, queue=self.queue_name, routing_key=self.routing_key)


    def on_request(self, ch, method, props, body):
        if self.host_object != None:
            self.host_object.on_message_received(ch, method, props, body)
        else:
            mess = json.loads(str(body.decode("utf-8")))
            LOGGER.info(mess)

    def start(self):
        try:
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.on_request, auto_ack=True)
            self.channel.start_consuming()
        # except pika.exceptions.StreamLostError as e:
        except Exception as e:
            LOGGER.info(e)
            LOGGER.exception("Connection lost. Reconnecting...")
            self._reconnect()
            self.start()

    def stop(self):
        self.channel.stop_consuming()
        self.channel.close()

    def get_queue(self):
        return self.queue.method.queue

    def _reconnect(self):
        self._setup_connection()