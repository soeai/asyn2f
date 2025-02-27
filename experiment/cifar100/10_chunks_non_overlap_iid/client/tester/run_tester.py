import os, sys
from dotenv import load_dotenv
import pause
from apscheduler.schedulers.background import BackgroundScheduler
import argparse


root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))))
sys.path.append(root)


from asynfed.client.client import Client
from asynfed.client.frameworks.tensorflow import TensorflowFramework

from experiment.cifar100.resnet20 import Resnet20
from experiment.cifar100.data_preprocessing import preprocess_dataset, get_file_id_in_csv, download_file_from_google_drive


import json 

load_dotenv()

scheduler = BackgroundScheduler()

# Create an argument parser
parser = argparse.ArgumentParser()
# Add arguments
parser.add_argument('--queue_exchange', dest='queue_exchange', type=str, 
                    default="cifar100-10-chunks-non-overlap-gpu", help='specify the queue exchange')

args = parser.parse_args()


with open('conf.json', 'r') as json_file:
    config = json.load(json_file)


# load queue config
config['queue_consumer']['endpoint'] = os.getenv("queue_consumer_endpoint")
config['queue_producer']['endpoint'] = os.getenv("queue_producer_endpoint")

config["queue_exchange"] = args.queue_exchange


import tensorflow as tf
print("*" * 20)
if tf.config.list_physical_devices('GPU'):
    tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[config['gpu_index']], 'GPU')
    print("Using GPU: ", tf.config.list_physical_devices('GPU')[config['gpu_index']])
else:
    print("Using CPU")
print("*" * 20)

# ------------oOo--------------------
# Preprocessing data
csv_filename = os.path.join(root, "experiment", "data", "cifar100", "10_chunks", "iid", "ggdrive_chunk_download_info.csv")

chunk_index = config['dataset']['chunk_index']
client_root_folder = os.path.dirname(os.getcwd())
# check whether data is on device, 
# if not, download from gg drive
local_data_folder = os.path.join(client_root_folder, "data")
# create data folder if it does not exist
if not os.path.exists(local_data_folder):
    os.makedirs(local_data_folder)

chunk_file_name = f"chunk_{chunk_index}.pickle"
local_file_path = os.path.join(local_data_folder, chunk_file_name)
if not os.path.isfile(local_file_path):
    print("Chunk data does not exist in local folder. Shortly begin to download")
    file_id = get_file_id_in_csv(csv_filename, chunk_index)
    download_file_from_google_drive(file_id= file_id, destination= local_file_path)
    print("Succesfully download data from google drive folder")
else:
    print("Dataset already exists in local data folder.")
    
# testset_filename = "test_set.pickle"
# default_testing_dataset_path = os.path.join(data_folder_path, testset_filename)

test_ds, data_size = preprocess_dataset(local_file_path, training = False)

# default_testing_dataset_path = "../../../../data/cifar_data/test_set.pickle"
# test_ds, data_size = preprocess_dataset(default_testing_dataset_path, training = False)
# ------------oOo--------------------

print("-" * 20)
print("-" * 20)
print(f"Begin testing global model performance with data size of {data_size}")
print("-" * 20)
print("-" * 20)

# Define model
model = Resnet20(input_features= (32, 32, 3),
                 output_features= 100)


# Define framework
tensorflow_framework = TensorflowFramework(model=model, 
                                           data_size= data_size, 
                                           test_ds= test_ds, 
                                           config=config)


client = Client(model= tensorflow_framework, config= config)

client.start()
scheduler.start()
pause.days(1) # or it can anything as per your need
