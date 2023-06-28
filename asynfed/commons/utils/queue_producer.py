import pika, uuid

class AmqpProducer(object):
    # Init an amqp client handling the connection to amqp servier
    def __init__(self, configuration: dict, log: bool = False):
        """
        AMQP connector
        configuration: a dictionary include broker and queue information
        log: a bool flag for logging message if being set to True, default is False
        """
        self.conf = configuration
        self.exchange_name = configuration["exchange_name"]
        self.exchange_type = configuration["exchange_type"]
        self.routing_key = configuration["routing_key"]
        self.log_flag = log

        # Connect to RabbitMQ host
        if "amqps://" in configuration["end_point"]:
            self.connection = pika.BlockingConnection(pika.URLParameters(configuration["end_point"]))
        else:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=configuration["end_point"]))

            # Create a channel
        self.channel = self.connection.channel()

        # Init an Exchange
        self.channel.exchange_declare(exchange=self.exchange_name, exchange_type=self.exchange_type)

    def send_data(self, body_mess, corr_id=None, routing_key=None, expiration=1000):
        # Sending data to desired destination
        # if sender is client, it will include the "reply_to" attribute to specify where to reply this message
        # if sender is server, it will reply the message to "reply_to" via default exchange
        if corr_id == None:
            corr_id = str(uuid.uuid4())
        if routing_key == None:
            routing_key = self.routing_key
        self.sub_properties = pika.BasicProperties(correlation_id=corr_id, expiration=str(expiration))
        self.channel.basic_publish(exchange=self.exchange_name, routing_key=routing_key,
                                   properties=self.sub_properties, body=body_mess)
        # if self.log_flag:
        #     self.mess_logging.log_request(body_mess,corr_id)

    def get(self):
        return self.conf
