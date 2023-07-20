import os, sys
from dotenv import load_dotenv
import pause
from apscheduler.schedulers.background import BackgroundScheduler

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))))
# root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))))
sys.path.append(root)



from asynfed.client.algorithms import ClientAsyncFl
from asynfed.client.frameworks.tensorflow import TensorflowFramework

from experiment.cifar_dataset.resnet18 import Resnet18
from experiment.cifar_dataset.data_preprocessing import preprocess_dataset


import json
import argparse

load_dotenv()

scheduler = BackgroundScheduler()


# Create an argument parser
parser = argparse.ArgumentParser()
# Add arguments
parser.add_argument('--config_file', dest='config_file', type=str, help='specify the config file for running')
parser.add_argument('--queue_exchange', dest='queue_exchange', type=str, default="20-chunks-second-try", help='specify the queue exchange')
# parser.add_argument('--queue_exchange', dest='queue_exchange', type=str, default="cifar10-20-chunks", help='specify the queue exchange')

# Parse the arguments
args = parser.parse_args()

with open(args.config_file, 'r') as json_file:
    config = json.load(json_file)

# load queue config
config['queue_consumer']['endpoint'] = os.getenv("queue_consumer_endpoint")
config['queue_producer']['endpoint'] = os.getenv("queue_producer_endpoint")

config["queue_exchange"] = args.queue_exchange


import tensorflow as tf

# avoid conflict

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
data_folder_path = os.path.join(root, "experiment", "data", "cifar_data")

testset_filename = "test_set.pickle"
default_testing_dataset_path = os.path.join(data_folder_path, testset_filename)

chunk_folder = os.path.join("20_chunks", "iid")
chunk_filename = f"chunk_{config['dataset']['chunk_index']}.pickle"
training_dataset_path = os.path.join(data_folder_path, chunk_folder, chunk_filename)

# default_testing_dataset_path = "../../../data/cifar_data/test_set.pickle"
# training_dataset_path = f"../../../data/cifar_data/5_chunks_1/iid/chunk_{config['dataset']['chunk_index']}.pickle"

train_ds, data_size = preprocess_dataset(training_dataset_path, batch_size = config['training_params']['batch_size'], training = True)
test_ds, _ = preprocess_dataset(default_testing_dataset_path, batch_size= config['training_params']['batch_size'], training = False)
# ------------oOo--------------------

config['dataset']['data_size'] = data_size


print("-" * 20)
print("-" * 20)
print(f"Begin training proceess with data size of {data_size}")
print("-" * 20)
print("-" * 20)

# Define model
model = Resnet18(input_features= (32, 32, 3), 
                 output_features= 10,
                 lr=config['training_params']['learning_rate'],
                 decay_steps=int(config['training_params']['decay_period'] * data_size / config['training_params']['batch_size']))


# Define framework
tensorflow_framework = TensorflowFramework(model=model, 
                                           data_size= data_size, 
                                           train_ds= train_ds, 
                                           test_ds= test_ds, 
                                           config=config)


tf_client = ClientAsyncFl(model=tensorflow_framework, config=config)
tf_client.start()
scheduler.start()
pause.days(1) # or it can anything as per your need
