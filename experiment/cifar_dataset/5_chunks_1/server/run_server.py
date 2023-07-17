import json
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))))
sys.path.append(root)

# from asynfed.commons.conf import Config
from asynfed.server import Server
from asynfed.server.strategies import AsynFL
from asynfed.commons.conf import Config

from dotenv import load_dotenv
load_dotenv()


with open('conf.json', 'r') as json_file:
    config = json.load(json_file)

# load minio key
config['cloud_storage']['minio']['access_key'] = os.getenv("minio_access_key")
config['cloud_storage']['minio']['secret_key'] = os.getenv("minio_secret_key")

config['cloud_storage']['minio']['client_access_key'] = os.getenv("minio_client_access_key")
config['cloud_storage']['minio']['client_secret_key'] = os.getenv("minio_client_secret_key")
config['cloud_storage']['minio']['endpoint_url'] = os.getenv("minio_endpoint_url")

# load influxdb config
config['influxdb']['url'] = os.getenv("INFLUXDB_URL")
config['influxdb']['token'] = os.getenv("INFLUXDB_TOKEN")
config['influxdb']['org'] = os.getenv("INFLUXDB_ORG")
config['influxdb']['bucket_name'] = os.getenv("INFLUXDB_BUCKET")

# load queue config
config['queue_consumer']['endpoint'] = os.getenv("queue_consumer_endpoint")
config['queue_producer']['endpoint'] = os.getenv("queue_producer_endpoint")

server_id = config.get("server_id") or "server-record"

Config.LOG_PATH = f"./{server_id}/{Config.LOG_PATH}"
Config.TMP_GLOBAL_MODEL_FOLDER = f"./{server_id}/{Config.TMP_GLOBAL_MODEL_FOLDER}"
Config.TMP_LOCAL_MODEL_FOLDER = f"./{server_id}/{Config.TMP_LOCAL_MODEL_FOLDER}"

strategy = AsynFL()
fedasync_server = Server(strategy, config)
fedasync_server.start()
