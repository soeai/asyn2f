import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))

# platform package
from asynfed.commons.conf import Config
from asynfed.client.algorithms.client_asyncfL import ClientAsyncFl

import argparse

# tensorflow 
from asynfed.client.frameworks.tensorflow.tensorflow_framework import TensorflowFramework
from data_preprocessing import TensorflowDataPreprocessing
from Lenet import LeNet


# Create an argument parser
parser = argparse.ArgumentParser(description='Example script with command-line arguments.')

# Add an argument
parser.add_argument('--training_exchange', dest='training_exchange', type=str, help='define training exchange to connect to rabbitMQ server')
# Parse the arguments
args = parser.parse_args()


# Preprocessing data
# mnist dataset
# Set the file paths for the MNIST digit dataset files
train_images_path = './data/mnist_data/train-images-idx3-ubyte.gz'
train_labels_path = './data/mnist_data/train-labels-idx1-ubyte.gz'
test_images_path = './data/mnist_data/t10k-images-idx3-ubyte.gz'
test_labels_path = './data/mnist_data/t10k-labels-idx1-ubyte.gz'


Config.QUEUE_URL = "amqp://guest:guest@13.214.37.45:5672/%2F"
Config.TRAINING_EXCHANGE = "test-server01234561011010101"
if args.training_exchange:
    Config.TRAINING_EXCHANGE = args.training_exchange

Config.MONITOR_QUEUE = "test"

# preprocessing data to be ready for low level tensorflow training process
data_preprocessing = TensorflowDataPreprocessing(train_images_path=train_images_path,
                                                 train_labels_path=train_labels_path, batch_size=64, split=True,
                                                 fract=0.2, evaluate_images_path=test_images_path,
                                                 evaluate_labels_path=test_labels_path)


# define dataset
train_ds = data_preprocessing.train_ds
test_ds = data_preprocessing.test_ds
evaluate_ds = data_preprocessing.evaluate_ds

data_size = 10000

# define model
lenet_model = LeNet(input_features = (32, 32, 1), output_features = 10)
# define framework
tensorflow_framework = TensorflowFramework(model = lenet_model, data_size= data_size, train_ds= train_ds, test_ds= test_ds)

tf_client = ClientAsyncFl(model=tensorflow_framework)
tf_client.run()
