import pika, json


class AmqpConsumer(object):
    # Init an amqp client handling the connection to amqp servier
    def __init__(self, configuration: dict, host_object: object = None):
        self.conf = configuration
        self.host_object = host_object
        self.exchange_name = configuration["exchange_name"]
        self.exchange_type = configuration["exchange_type"]
        self.routing_key = configuration["routing_key"]
        self._connect()
    
    def _connect(self):
        # Connect to RabbitMQ host
        if "amqps://" in self.conf["end_point"]:
            self.connection = pika.BlockingConnection(pika.URLParameters(self.conf["end_point"]))
        else:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.conf["end_point"]))

        # Create a channel
        self.channel = self.connection.channel()

        # Init an Exchange
        self.channel.exchange_declare(exchange=self.exchange_name, exchange_type=self.exchange_type)

        # Declare a queue to receive prediction response
        self.queue = self.channel.queue_declare(queue=self.conf["queue_name"], exclusive=False)
        self.queue_name = self.queue.method.queue
        # Binding the exchange to the queue with specific routing
        self.channel.queue_bind(exchange=self.exchange_name, queue=self.queue_name, routing_key=self.routing_key)

    def on_request(self, ch, method, props, body):
        # Process the data on request: sending back to host object
        if self.host_object != None:
            self.host_object.on_message_received(ch, method, props, body)
        else:
            mess = json.loads(str(body.decode("utf-8")))
            print(mess)

    def start(self):
        # Start rabbit MQ
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.on_request, auto_ack=True)
        self.channel.start_consuming()

    def stop(self):
        self.channel.stop_consuming()
        self.channel.close()

    def get_queue(self):
        return self.queue.method.queue
