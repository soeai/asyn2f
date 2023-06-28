import os, sys
project_dir = os.path.dirname(os.path.dirname(os.getcwd()))
sys.path.append(project_dir)

from uuid import uuid4
from asynfed.commons.messages.response_client_connection import ResponseClientConnection
from threading import Thread
from asynfed.commons.utils import queue_consumer, queue_producer
from asynfed.commons.messages import message_v2


class AmqpServer:
    def __init__(self, config):
        self.config = config
        self.amqp_consumer = queue_consumer.AmqpConsumer(config['queue_consumer'], self)
        self.amqp_producer = queue_producer.AmqpProducer(config['queue_producer'])
        self.amqp_thread = Thread(target=self.start)

    def on_message_received(self, ch, method, props, body):
        msg_received = eval(body.decode('utf-8'))
        print(f" [x] Server received {msg_received}")

        if msg_received['message_type'] == 'init_connection':
            self._handle_init_connection(msg_received)
            print(f" [x] Server sent {msg_received}")




    def start(self):
        self.amqp_consumer.start()

    def start_amqp(self):
        self.amqp_thread.start()

    def _handle_init_connection(self, msg_received):
        client_profile = { "client_identifier": str(uuid4()),
            "session_id": msg_received['headers']['session_id'],
            "client_id": str(uuid4()) }
        storage_info = { "access_key": "access_key",
            "secret_key": "secret_key",
            "bucket_name": "testbucket",
            "region_name": "asia-southeast-1", }
        model_info = { "global_model_name": "global_model_name",
            "model_version": "model_version",
            "model_url": "model_url" }
        queue_info = { 'monitor_exchange': 'monitor_exchange',
                'training_exchange': 'training_exchange', }

        content = ResponseClientConnection(client_profile, storage_info, model_info, queue_info)
        message = message_v2.MessageV2(message_type="response_connection", content=content).to_json()
        self.amqp_producer.send_message(message, routing_key='client_consumer')

if __name__ == '__main__':
    config = {
        'queue_consumer': {
            'host': 'gocktdwu',
            'port': 5672,
            'queue_name': 'client_queue',
            'exchange_name': 'test_exchange',
            'exchange_type': 'topic',
            'routing_key': 'server.#',
            'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu',
        },
        'queue_producer': {
            'host': 'gocktdwu',
            'port': 5672,
            'queue_name': 'server_queue',
            'exchange_name': 'test_exchange',
            'exchange_type': 'topic',
            'routing_key': 'worker.w1',
            'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu',
        },
    }
    server = AmqpServer(config)
    server.start_amqp()
