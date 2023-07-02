import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.append(root)

from asynfed.commons.conf import Config
from asynfed.server.server_v2 import Server
from asynfed.server.strategies.AsynFL import AsynFL

from dotenv import load_dotenv
load_dotenv()

Config.STORAGE_ACCESS_KEY = os.getenv("access_key")
Config.STORAGE_SECRET_KEY = os.getenv("secret_key")

conf = {
    "server_id": "test_server_id",
    "bucket_name": "test-client-v2-cifar10-resnet-5-chunks-14",
    "region_name": "ap-southeast-2",
    "t": 30,
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
