import json
import os, sys
import argparse

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))))
sys.path.append(root)

# from asynfed.server.algorithms import Asyn2fServer, KAFLMStepServer
# from asynfed.server.strategies import Asyn2fStrategy

from asynfed.server import Server

from dotenv import load_dotenv
load_dotenv()

# Create an argument parser
parser = argparse.ArgumentParser()
# Add arguments

parser.add_argument('--config_file', dest='config_file', type=str, default= "asyn2f.json",
                     help='specify the config file for running')
parser.add_argument('--use_loss', dest='use_loss', type=bool, default= True,
                     help='specify whether to use loss to compute weighted for fedavg')

# Parse the arguments
args = parser.parse_args()

with open(args.config_file, 'r') as json_file:
    config = json.load(json_file)
    
# with open(args.config_file, 'r') as json_file:
#     config = json.load(json_file)

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

if config['strategy']['name'] == "fedavg":

    print(args.use_loss)
    use_loss = config['strategy']['use_loss'] or args.use_loss
    config['strategy']['use_loss'] = use_loss
    config['strategy']['beta'] = 0.5
    
server = Server(config= config)

server.start()

