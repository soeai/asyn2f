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
from data_preprocessing import TensorflowImageDataPreprocessing
from Lenet import LeNet


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
train_images_path = os.path.join(root, os.getenv("x_train_path"))
train_labels_path = os.path.join(root, os.getenv("y_train_path"))
test_images_path = os.path.join(root, os.getenv("x_test_path"))
test_labels_path = os.path.join(root, os.getenv("y_test_path"))


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
data_preprocessing = TensorflowImageDataPreprocessing(train_images_path=train_images_path, train_labels_path=train_labels_path, 
                                                      height = 28, width = 28, batch_size=Config.BATCH_SIZE, split=True, fract=0.2,
                                                      evaluate_images_path=test_images_path, evaluate_labels_path=test_labels_path)
# define dataset
train_ds = data_preprocessing.train_ds
test_ds = data_preprocessing.test_ds
evaluate_ds = data_preprocessing.evaluate_ds
# ------------oOo--------------------

qod = 0.45
epoch = 10
delta_time = 15





# define model
lenet_model = LeNet(input_features = (28, 28, 1), output_features = 10)
# define framework
tensorflow_framework = TensorflowFramework(model = lenet_model, epoch= epoch, delta_time= delta_time, data_size= Config.DATA_SIZE, qod= qod, train_ds= train_ds, test_ds= test_ds)

tf_client = ClientAsyncFl(model=tensorflow_framework)
tf_client.run()
