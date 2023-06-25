import os
import sys
from dotenv import load_dotenv
import argparse

# run locally without install asynfed package
root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.append(root)
from asynfed.client.algorithms.client_asyncfL import ClientAsyncFl
from asynfed.commons.conf import Config

# tensorflow 
from asynfed.client.frameworks.tensorflow.tensorflow_framework import TensorflowFramework
from data_preprocessing import *
from Lenet import LeNet


# Create an argument parser
parser = argparse.ArgumentParser(description='Example script with command-line arguments.')
# Add arguments
parser.add_argument('--queue_url', dest='queue_url', type=str, help='specify the url of RabbitMQ server')
parser.add_argument('--training_exchange', dest='training_exchange', type=str, help='define training exchange to connect to rabbitMQ server')
parser.add_argument('--gpu_index', dest='gpu_index', type=int, help='specify the gpu uses of the training process')

# Parse the arguments
args = parser.parse_args()

# load env variables
load_dotenv()

Config.QUEUE_URL = os.getenv("queue_url")
if args.queue_url:
    Config.QUEUE_URL = args.queue_url

Config.TRAINING_EXCHANGE = os.getenv("training_exchange")
if args.training_exchange:
    Config.TRAINING_EXCHANGE = args.training_exchange



print("*" * 20)
if args.gpu_index is not None:
   print(f"config gpu_index: {args.gpu_index}")
   gpu_index = args.gpu_index
else:
   print("no gpu index set, set default as 0")
   gpu_index = 0
print("*" * 20)


print("*" * 20)
print("*" * 20)
import tensorflow as tf
if tf.config.list_physical_devices('GPU'):
    tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[gpu_index], 'GPU')
    print("config tensorflow using gpu successfully")
else:
    print("There is no gpu or your tensorflow is not built in with gpu support")
print("*" * 20)
print("*" * 20)

# ------------oOo--------------------
# Preprocessing data
# mnist dataset
# Set the file paths for the MNIST digit dataset files
train_images_path = os.path.join(root, os.getenv("mnist_x_train_path"))
train_labels_path = os.path.join(root, os.getenv("mnist_y_train_path"))
test_images_path = os.path.join(root, os.getenv("mnist_x_test_path"))
test_labels_path = os.path.join(root, os.getenv("mnist_y_test_path"))


if os.getenv("batch_size"):
    Config.BATCH_SIZE = int(os.getenv("batch_size"))
else:
    Config.BATCH_SIZE = 128

if os.getenv("data_size"):
    Config.DATA_SIZE = int(os.getenv("data_size"))
else:
    Config.DATA_SIZE = 60000

# for tracking process when training
if os.getenv("tracking_point"):
    Config.TRACKING_POINT = int(os.getenv("tracking_point"))
else:
    Config.TRACKING_POINT = 10000

if os.getenv("sleeping_time"):
    Config.SLEEPING_TIME= int(os.getenv("sleeping_time"))
else:
    Config.SLEEPING_TIME= 3

# preprocessing data to be ready for low level tensorflow training process
train_ds, data_size = preprocess_dataset(images_path= train_images_path, labels_path= train_labels_path, training= True)
test_ds, _ = preprocess_dataset(images_path= test_images_path, labels_path= test_labels_path, training= False)
# ------------oOo--------------------


print("-" * 20)
print("-" * 20)
print(f"Begin training proceess with data size of {data_size}")
print("-" * 20)
print("-" * 20)

# define model
model = LeNet()
# define framework
tensorflow_framework = TensorflowFramework(model = model, epoch= 200, data_size= data_size, train_ds= train_ds, test_ds= test_ds, delta_time= 10000, qod= 0.45)

tf_client = ClientAsyncFl(model=tensorflow_framework)
tf_client.run()

