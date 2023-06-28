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
# queue
# storage
Config.STORAGE_ACCESS_KEY = os.getenv("access_key")
Config.STORAGE_SECRET_KEY = os.getenv("secret_key")

print(os.getenv("access_key"))
print(os.getenv("secret_key"))

# local saving directories
Config.TMP_LOCAL_MODEL_FOLDER = os.getenv("local_model_folder")
Config.TMP_GLOBAL_MODEL_FOLDER = os.getenv("global_model_folder")
# Config.LOG_PATH = os.getenv("log_path")

parser = argparse.ArgumentParser(description='Example script with command-line arguments.')


# connection config
parser.add_argument('--queue_url', dest='queue_url', type=str, help='specify the url of RabbitMQ server')
parser.add_argument('--training_exchange', dest='training_exchange', type=str, help='define training exchange to connect to rabbitMQ server')
parser.add_argument('--bucket_name', dest='bucket_name', type=str, help='define training exchange to connect to rabbitMQ server')

args = parser.parse_args()

if args.queue_url:
    Config.QUEUE_URL = args.queue_url
else:
    Config.QUEUE_URL = os.getenv("queue_url")


if args.bucket_name:
    bucket_name = args.bucket_name
else:
    if os.getenv("bucket_name"):
        bucket_name = os.getenv("bucket_name")
        print(f"choose bucket name as : {bucket_name}")
    else:
        # bucket_name= 'test-client-tensorflow-mnist'
        bucket_name= 'test-client-tensorflow-cifar10'


if args.training_exchange:
    Config.TRAINING_EXCHANGE = args.training_exchange
else:
    if os.getenv("training_exchange"):
        training_exchange = os.getenv("training_exchange")
        print(f"choose training exchange as : {training_exchange}")
    else:
        # training_exchange= 'test-client-tensorflow-mnist'
        training_exchange= 'test-client-tensorflow-cifar10'


# # load test dataset
# from data_preprocessing import preprocess_dataset
# default_testing_dataset_path = "../../data/cifar_data/test_set.pickle"
# test_ds, _ = preprocess_dataset(default_testing_dataset_path, training = False)

config = {}

strategy = AsynFL()
fedasync_server = Server(strategy, config, t= 40, test = True, training_exchange= training_exchange, bucket_name= bucket_name)


fedasync_server.start()
