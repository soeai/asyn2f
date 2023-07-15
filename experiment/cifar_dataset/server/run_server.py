import json
import os, sys
root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.append(root)

# from asynfed.commons.conf import Config
from asynfed.server import Server
from asynfed.server.strategies import AsynFL

from dotenv import load_dotenv
load_dotenv()


with open('conf.json', 'r') as json_file:
    config = json.load(json_file)

# load minio key
config['cloud_storage']['minio']['access_key'] = os.getenv("minio_access_key")
config['cloud_storage']['minio']['secret_key'] = os.getenv("minio_secret_key")

config['cloud_storage']['minio']['client_access_key'] = os.getenv("client_access_key")
config['cloud_storage']['minio']['client_secret_key'] = os.getenv("client_secret_key")

# load influxdb config
config['influxdb']['url'] = os.getenv("INFLUXDB_URL")
config['influxdb']['token'] = os.getenv("INFLUXDB_TOKEN")
config['influxdb']['org'] = os.getenv("INFLUXDB_ORG")
config['influxdb']['bucket_name'] = os.getenv("INFLUXDB_BUCKET")


strategy = AsynFL()
fedasync_server = Server(strategy, config)
fedasync_server.start()
