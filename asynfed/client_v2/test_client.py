
import os, sys
project_dir = os.path.dirname(os.path.dirname(os.getcwd()))
sys.path.append(project_dir)

from threading import Thread
from asynfed.commons.utils import queue_consumer, queue_producer
from asynfed.commons.messages import message_v2
from asynfed.client_v2.messages import init_connection


class AmqpClient:
    def __init__(self, config):
        self.config = config
        self.amqp_consumer = queue_consumer.AmqpConsumer(config['queue_consumer'], self)
        self.amqp_producer = queue_producer.AmqpProducer(config['queue_producer'])
        self.send_init_message()
        self.amqp_thread = Thread(target=self.start)

    def on_message_received(self, ch, method, props, body):
        msg_received = eval(body.decode('utf-8'))
        
        if msg_received['message_type'] == 'response_connection':
            print(f" [x] Client received {msg_received}")

    def start(self):
        self.amqp_consumer.start()

    def start_amqp(self):
        self.amqp_thread.start()

    def send_init_message(self):
        content = init_connection.InitConnection()

        message = message_v2.MessageV2(
            message_type='init_connection',
            headers={'session_id': 'session_1', 'client_id': 'client_1'},
            content=content

        ).to_json()
        print(f" [x] Client sent {message}")
        self.amqp_producer.send_message(message)
        




if __name__ == '__main__':
    config = {
        'queue_consumer': {
            'host': 'gocktdwu',
            'port': 5672,
            'queue_name': 'server_queue',
            'exchange_name': 'test_exchange',
            'exchange_type': 'topic',
            'routing_key': 'default',
            'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu',
        },
        'queue_producer': {
            'host': 'gocktdwu',
            'port': 5672,
            'queue_name': 'client_queue',
            'exchange_name': 'test_exchange',
            'exchange_type': 'topic',
            'routing_key': 'default',
            'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu',
        },
    }
    server = AmqpClient(config)
    server.start_amqp()
