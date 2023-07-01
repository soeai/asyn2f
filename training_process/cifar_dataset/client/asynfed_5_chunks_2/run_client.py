import os
import sys
from dotenv import load_dotenv
import argparse

# run locally without install asynfed package
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))))
sys.path.append(root)
# training_path = f"{root}/training_process"
# sys.path.append(training_path)
# asynfed lib
from asynfed.client.algorithms.client_asyncfL import ClientAsyncFl
from asynfed.commons.conf import Config

# tensorflow 
from asynfed.client.frameworks.tensorflow.tensorflow_framework import TensorflowFramework
from training_process.cifar_dataset.client.resnet18 import Resnet18

from data_preprocessing import preprocess_dataset

# Create an argument parser
parser = argparse.ArgumentParser(description='Example script with command-line arguments.')
# Add arguments
parser.add_argument('--chunk_index', dest='chunk_index', type= int, help='choose which chunk to run client on')

# connection config
parser.add_argument('--queue_url', dest='queue_url', type=str, help='specify the url of RabbitMQ server')
parser.add_argument('--training_exchange', dest='training_exchange', type=str, help='define training exchange to connect to rabbitMQ server')

# training params config
parser.add_argument('--gpu_index', dest='gpu_index', type=int, help='specify the gpu uses of the training process')
parser.add_argument('--batch_size', dest='batch_size', type=int, help='specify the batch_size of the training process')
parser.add_argument('--epoch', dest='epoch', type=int, help='specify the epoch of the training process')

# Parse the arguments
args = parser.parse_args()
# load env variables
load_dotenv()

# ------------oOo--------------------
Config.QUEUE_URL = os.getenv("queue_url")
if args.queue_url:
    Config.QUEUE_URL = args.queue_url

Config.TRAINING_EXCHANGE = os.getenv("training_exchange")
if args.training_exchange:
    Config.TRAINING_EXCHANGE = args.training_exchange
# ------------oOo--------------------


# ------------oOo--------------------
if args.batch_size:
    Config.BATCH_SIZE = args.batch_size
else:
    if os.getenv("batch_size"):
        Config.BATCH_SIZE = int(os.getenv("batch_size"))
    else:        
        # default batch size = 128
        Config.BATCH_SIZE = 128

if args.epoch:
    Config.EPOCH = args.epoch
else:
    if os.getenv("epoch"):
        Config.EPOCH = int(os.getenv("epoch"))
    else:
        Config.EPOCH = 200
# ------------oOo--------------------




print("*" * 20)
if args.gpu_index is not None:
   print(f"config gpu_index: {args.gpu_index}")
   gpu_index = args.gpu_index
else:
   print("no gpu index set, set default as 0")
   gpu_index = 0
print("*" * 20)


# print("*" * 20)
# print("*" * 20)
# import tensorflow as tf
# if tf.config.list_physical_devices('GPU'):
#     tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[gpu_index], 'GPU')
#     print("config tensorflow using gpu successfully")
# else:
#     print("There is no gpu or your tensorflow is not built in with gpu support")
# print("*" * 20)
# print("*" * 20)


# ------------oOo--------------------
# for tracking process when training
if os.getenv("tracking_point"):
    Config.TRACKING_POINT = int(os.getenv("tracking_point"))
else:
    Config.TRACKING_POINT = 1000

if os.getenv("sleeping_time"):
    Config.SLEEPING_TIME= int(os.getenv("sleeping_time"))
else:
    Config.SLEEPING_TIME= 3
# ------------oOo--------------------

# set default qod now for all dataset
qod = 0.45

# ------------oOo--------------------
# Preprocessing data
default_training_dataset_path = "../../../data/cifar_data/5_chunks/chunk_2.pickle"
default_testing_dataset_path = "../../../data/cifar_data/test_set.pickle"
if args.chunk_index:
    print("*" * 20)
    print(f"CHOOSEN CHUNK: {args.chunk_index}")
    print("*" * 20)
    training_dataset_path = f"../../../data/cifar_data/5_chunks/chunk_{args.chunk_index}.pickle"
else:
    if os.getenv("cifar_train_dataset_path"):
        training_dataset_path = os.getenv("cifar_train_dataset_path")
    else:
        training_dataset_path = default_training_dataset_path
    

# train_ds, data_size = preprocess_dataset(training_dataset_path, training = True)
# test_ds, _ = preprocess_dataset(testing_dataset_path, training = False)
train_ds, data_size = preprocess_dataset(training_dataset_path, batch_size = 128, training = True)
test_ds, _ = preprocess_dataset(default_testing_dataset_path, training = False)
# train_ds, data_size = preprocess_dataset("training_process/data/cifar_data/5_chunks/chunk_2.pickle", training = True)
# test_ds, _ = preprocess_dataset("training_process/data/cifar_data/test_set.pickle", training = False)
# ------------oOo--------------------

print("-" * 20)
print("-" * 20)
print(f"Begin training proceess with data size of {data_size}")
print("-" * 20)
print("-" * 20)

# define model
model = Resnet18(input_features= (32, 32, 3), output_features= 10,
                 lr=1e-1, decay_steps=int(Config.EPOCH * data_size / Config.BATCH_SIZE))
# define framework
tensorflow_framework = TensorflowFramework(model = model, epoch= Config.EPOCH, data_size= data_size, train_ds= train_ds, test_ds= test_ds, regularization='l2', delta_time= 10000, qod= 0.45)

tf_client = ClientAsyncFl(model=tensorflow_framework)
tf_client.run()
