import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))))

from fedasync.commons.conf import Config
from fedasync.client.algorithms.client_asyncfL import ClientAsyncFl
from fedasync.client.frameworks.tensorflow import TensorflowModel

from data_preprocessing import TensorflowDataPreprocessing
# from ..tensorflow_examples.mnist.tensorflow import TensorflowModel
from Lenet import LeNet
# import tensorflow as tf

# Preprocessing data
# mnist dataset
# Set the file paths for the MNIST digit dataset files
train_images_path = '../data/mnist_data/train-images-idx3-ubyte.gz'
train_labels_path = '../data/mnist_data/train-labels-idx1-ubyte.gz'
test_images_path = '../data/mnist_data/t10k-images-idx3-ubyte.gz'
test_labels_path = '../data/mnist_data/t10k-labels-idx1-ubyte.gz'

Config.QUEUE_URL = "amqps://bxvrtbsf:RYNaloqSceK4YD59EQL44t-nYaWpVlnO@whale.rmq.cloudamqp.com/bxvrtbsf"

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
lenet_model = LeNet()
# define framework
tensorflow_framework = TensorflowModel(model = lenet_model, data_size= data_size, train_ds= train_ds, test_ds= test_ds)

tf_client = ClientAsyncFl(model= tensorflow_framework)
tf_client.run()
