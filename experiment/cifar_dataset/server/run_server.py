import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.append(root)

# from asynfed.commons.conf import Config
from asynfed.server import Server
from asynfed.server.strategies import AsynFL

from dotenv import load_dotenv
load_dotenv()


conf = {
    "server_id": "",
    "update_period": 30,
    "ping_time": 300,
    "save_log": True,

  "cloud_storage": {
        "type": "minio",

        "bucket_name": "test-refactor-code-2",


        "aws_s3": {
            "access_key": "",
            "secret_key": "",
            "region_name": "ap-southeast-2",
            },

        "minio": {
            "access_key": os.getenv("minio_access_key"),
            "secret_key": os.getenv("minio_secret_key"),

            "client_access_key": os.getenv("client_access_key"),
            "client_secret_key": os.getenv("client_secret_key"),
            "endpoint_url": "http://128.214.254.126:9000",


            "region_name": "ap-southeast-2",
        },
        
        "cleaning_config": {
            "clean_cloud_storage_period": 30,
            "global_keep_version_num": 5,
            "local_keep_version_num": 3,
        },
    },
    "queue_consumer": {
        'exchange_name': 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_consumer',
        'routing_key': 'server.#',
        # 'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu'
        'end_point': 'amqps://vxfoxzgj:RwGa4xE5h5PIVvUFTcOje1KZ_J_b0j9Y@armadillo.rmq.cloudamqp.com/vxfoxzgj'
    },
    "queue_producer": {
        'exchange_name': 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_queue',
        'routing_key': 'client.#',
        # 'end_point': "amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu"
        'end_point': "amqps://vxfoxzgj:RwGa4xE5h5PIVvUFTcOje1KZ_J_b0j9Y@armadillo.rmq.cloudamqp.com/vxfoxzgj"
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
fedasync_server = Server(strategy, conf)
fedasync_server.start()
