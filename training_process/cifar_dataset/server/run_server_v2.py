import os, sys
# run locally without install asynfed package
root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.append(root)

# asynfed lib
from asynfed.commons.conf import Config
from asynfed.server.server_v2 import Server
from asynfed.server.strategies.AsynFL import AsynFL

# env config
from dotenv import load_dotenv
import argparse


load_dotenv()
Config.STORAGE_ACCESS_KEY = os.getenv("access_key")
Config.STORAGE_SECRET_KEY = os.getenv("secret_key")


conf = {
    "server_id": "test_server_id",
    "bucket_name": "test-client-cifar10-5-chunks-17",
    "queue_consumer": {
        'exchange_name': 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_consumer',
        'routing_key': 'server.#',
        'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu'
    },
    "queue_producer": {
        'exchange_name': 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_queue',
        'routing_key': 'client.#',
        'end_point': "amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu"
    }
}
strategy = AsynFL()
fedasync_server = Server(strategy, conf)


fedasync_server.start()
