import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.append(root)

# from asynfed.commons.conf import Config
from asynfed.server import Server
from asynfed.server.strategies import AsynFL

from dotenv import load_dotenv
load_dotenv()


conf = {
    "server_id": "test_server_id",
    "t": 30,
    "stop_conditions": {
        "max_version": 300,
        "max_performance": 0.95,
        "min_loss": 0.02,
    },
    "model_exchange_at":{
        # "performance": 0.85,
        # "epoch": 100
        "performance": 0.35,
        "epoch": 3
    },
    "aws": {
        "access_key": os.getenv("aws_access_key"),
        "secret_key": os.getenv("aws_secret_key"),

        "bucket_name": "cifar10-5-chunks",
        # "bucket_name": "test-lost-connection-4",
        "region_name": "ap-southeast-2",
    },
    "minio": {
        "access_key": os.getenv("minio_access_key"),
        "secret_key": os.getenv("minio_secret_key"),

        "client_access_key": os.getenv("client_access_key"),
        "client_secret_key": os.getenv("client_secret_key"),
        "endpoint_url": "http://128.214.254.126:9000",

        # "bucket_name": "test-cifar-client-5-chunks",
        "bucket_name": "test-aggregating-formula",
        "region_name": "ap-southeast-2",
    },

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
    },
    "influxdb": {
        "url": os.getenv("INFLUXDB_URL"),
        "token": os.getenv("INFLUXDB_TOKEN"),
        "org": os.getenv("INFLUXDB_ORG"),
        "bucket_name": os.getenv("INFLUXDB_BUCKET")
    }
}
strategy = AsynFL()
# fedasync_server = Server(strategy, conf, storage= "minio", save_log=True)
fedasync_server = Server(strategy, conf, storage= "minio", save_log=False)
fedasync_server.start()
