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
from VGG16 import VGG16
from resnet18 import Resnet18
from utils import *
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


if os.getenv("batch_size"):
    Config.BATCH_SIZE = int(os.getenv("batch_size"))
else:
    Config.BATCH_SIZE = 128

if os.getenv("data_size"):
    Config.DATA_SIZE = int(os.getenv("data_size"))
else:
    Config.DATA_SIZE = 50000

if os.getenv("epoch"):
    Config.EPOCH = int(os.getenv("epoch"))
else:
    Config.EPOCH = 200

if os.getenv("delta_time"):
    Config.DELTA_TIME = int(os.getenv("delta_time"))
else:
    Config.DELTA_TIME = 15


# for tracking process when training
if os.getenv("tracking_point"):
    Config.TRACKING_POINT = int(os.getenv("tracking_point"))
else:
    Config.TRACKING_POINT = 10000

if os.getenv("sleeping_time"):
    Config.SLEEPING_TIME= int(os.getenv("sleeping_time"))
else:
    Config.SLEEPING_TIME= 3

if tf.config.list_physical_devices('GPU'):
    tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[0], 'GPU')
else:
    print("There is no gpu or your tensorflow is not built in with gpu support")

# set qod
# qod = 0.45


# preprocessing data to be ready for low level tensorflow training process
# Preprocessing data
# mnist dataset
# Set the file paths for the MNIST digit dataset files
# data_path = "../../data/cifar_data/chunks/chunk_1.pickle"
# train_ds, test_ds, data_size = load_training_dataset(train_dataset_path= data_path)


# # augmented data
# augmentations_per_image = 10
# train_ds = generate_augmented_data(train_ds, batch_size= Config.BATCH_SIZE, augmentations_per_image= augmentations_per_image)


# set qod
qod = 0.45

print('==> Preparing data...')
train_images, train_labels, test_images, test_labels = get_dataset()
mean, std = get_mean_and_std(train_images)
train_images = normalize(train_images, mean, std)
test_images = normalize(test_images, mean, std)

train_ds = dataset_generator(train_images, train_labels, Config.BATCH_SIZE)
test_ds = tf.data.Dataset.from_tensor_slices((test_images, test_labels)).\
        batch(Config.BATCH_SIZE).prefetch(buffer_size=tf.data.experimental.AUTOTUNE)

# define model
# vgg_model = VGG16(input_features = (32, 32, 3), output_features = 10)
model = Resnet18(input_features = (32, 32, 3), output_features = 10, lr=1e-1, decay_steps=Config.EPOCH * Config.DATA_SIZE / Config.BATCH_SIZE)
# define framework
tensorflow_framework = TensorflowFramework(model = model, epoch= Config.EPOCH, delta_time= Config.DELTA_TIME, data_size= Config.DATA_SIZE, qod= qod, train_ds= train_ds, test_ds= test_ds)
#
# tf_client = ClientAsyncFl(model=tensorflow_framework)
# tf_client.run()

for epoch in range(Config.EPOCH):
    tensorflow_framework.model.train_loss.reset_states()
    tensorflow_framework.model.train_accuracy.reset_states()
    tensorflow_framework.model.test_loss.reset_states()
    tensorflow_framework.model.test_accuracy.reset_states()
    for images, labels in tensorflow_framework.train_ds:
        # get the previous weights before the new training process within each batch
        # self.model.previous_weights = self.model.get_weights()
        # training normally
        train_acc, train_loss= tensorflow_framework.fit(images, labels)

    for test_images, test_labels in tensorflow_framework.test_ds:
        test_acc, test_loss = tensorflow_framework.evaluate(test_images, test_labels)

    print("Epoch {} - Train Acc: {:.2f} -- Train Loss {} Test Acc {:.3f}  Test Loss {}".format(epoch+1,
                                                                                       train_acc * 100,
                                                                                       train_loss,
                                                                                       test_acc * 100,
                                                                                       test_loss))
