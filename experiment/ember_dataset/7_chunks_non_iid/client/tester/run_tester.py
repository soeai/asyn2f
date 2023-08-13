import os, sys
from dotenv import load_dotenv
import pause
from apscheduler.schedulers.background import BackgroundScheduler

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))))
sys.path.append(root)


from asynfed.client import Client

from asynfed.client.frameworks.tensorflow import TensorflowFramework

from experiment.ember_dataset.ember_model import EmberModel
from experiment.ember_dataset.data_preprocessing import DataLoader, download_file_from_google_drive, get_file_id_in_csv


import json
import argparse

load_dotenv()

scheduler = BackgroundScheduler()


# Create an argument parser
parser = argparse.ArgumentParser()
# Add arguments
parser.add_argument('--queue_exchange', dest='queue_exchange', type=str, default="ember-7-chunks-non-iid", help='specify the queue exchange')


# Parse the arguments
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
    gpu_index = config.get('gpu_index') or 0
    tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[gpu_index], 'GPU')
    print("Using GPU: ", tf.config.list_physical_devices('GPU')[gpu_index])
else:
    print("Using CPU")
print("*" * 20)


# ------------oOo--------------------
# Preprocessing data
csv_filename = os.path.join(root, "experiment", "data", "ember_data", "7_chunks", "non_iid", "ggdrive_chunk_download_info.csv")

chunk_index = config['dataset']['chunk_index']
save_path = f"chunk_{chunk_index}.pkl"

file_id = get_file_id_in_csv(csv_filename, chunk_index)
download_file_from_google_drive(file_id= file_id, destination= save_path)

data_loader = DataLoader(save_path)

data_size = data_loader.get_dataset_size()
class_weight = None
num_input_features = data_loader.get_num_input_features()

print(f"Data size: {data_size}, number of features: {num_input_features}, class weight: {class_weight}")
dataset = data_loader.create_tensorflow_dataset()

# ------------oOo--------------------
config['dataset']['data_size'] = data_size



print("-" * 20)
print("-" * 20)
print(f"Begin testing global model performance with data size of {data_size}")
print("-" * 20)
print("-" * 20)


model = EmberModel(input_features= num_input_features, output_features= 1, 
                    lr_config= {}, 
                    class_weight= class_weight)

# Define framework
tensorflow_framework = TensorflowFramework(model= model, 
                                           data_size= data_size, 
                                           train_ds= None, 
                                           test_ds= dataset, 
                                           config= config)


client = Client(model= tensorflow_framework, config= config)

client.start()
scheduler.start()
pause.days(1) # or it can anything as per your need
