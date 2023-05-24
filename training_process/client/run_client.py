import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))

# platform package
from asynfed.client.algorithms.client_asyncfL import ClientAsyncFl
from asynfed.commons.conf import Config

# tensorflow 
from asynfed.client.frameworks.tensorflow.tensorflow_framework import TensorflowFramework
from data_preprocessing import TensorflowImageDataPreprocessing
from Lenet import LeNet


# load env variables
from dotenv import load_dotenv
import argparse


# Create an argument parser
parser = argparse.ArgumentParser(description='Example script with command-line arguments.')
# Add arguments
parser.add_argument('--queue_url', dest='queue_url', type=str, help='specify the url of RabbitMQ server')
parser.add_argument('--training_exchange', dest='training_exchange', type=str, help='define training exchange to connect to rabbitMQ server')

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



# ------------oOo--------------------
# Preprocessing data
# mnist dataset
# Set the file paths for the MNIST digit dataset files
train_images_path = os.getenv("x_train_path")
train_labels_path = os.getenv("y_train_path")
test_images_path = os.getenv("x_test_path")
test_labels_path = os.getenv("y_test_path")

# preprocessing data to be ready for low level tensorflow training process
data_preprocessing = TensorflowImageDataPreprocessing(train_images_path=train_images_path, train_labels_path=train_labels_path, 
                                                      height = 28, width = 28, batch_size=64, split=True, fract=0.2,
                                                      evaluate_images_path=test_images_path, evaluate_labels_path=test_labels_path)
# define dataset
train_ds = data_preprocessing.train_ds
test_ds = data_preprocessing.test_ds
evaluate_ds = data_preprocessing.evaluate_ds
# ------------oOo--------------------

data_size = 10000

# define model
lenet_model = LeNet(input_features = (32, 32, 1), output_features = 10)
# define framework
tensorflow_framework = TensorflowFramework(model = lenet_model, data_size= data_size, train_ds= train_ds, test_ds= test_ds)

tf_client = ClientAsyncFl(model=tensorflow_framework)
tf_client.run()
