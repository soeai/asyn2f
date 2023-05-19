import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))))

from asynfed.commons.conf import Config
from asynfed.client.client_asyncfL import ClientAsyncFl
from test.tensorflow_examples.mnist.lenet_model import LeNet
from test.tensorflow_examples.mnist.data_preprocessing import TensorflowDataPreprocessing
# import tensorflow as tf




# Preprocessing data
# mnist dataset
# Set the file paths for the MNIST digit dataset files
train_images_path = '../data/mnist_data/train-images-idx3-ubyte.gz'
train_labels_path = '../data/mnist_data/train-labels-idx1-ubyte.gz'
test_images_path = '../data/mnist_data/t10k-images-idx3-ubyte.gz'
test_labels_path = '../data/mnist_data/t10k-labels-idx1-ubyte.gz'

# Config.QUEUE_URL = "amqps://bxvrtbsf:RYNaloqSceK4YD59EQL44t-nYaWpVlnO@whale.rmq.cloudamqp.com/bxvrtbsf"

Config.QUEUE_URL = "amqp://guest:guest@13.214.37.45:5672/%2F"
Config.TRAINING_EXCHANGE = "server_076dc8b4-1238-4786-bfdd-90cf60fe9462S3"

# preprocessing data to be ready for low level tensorflow training process
data_preprocessing = TensorflowDataPreprocessing(train_images_path=train_images_path,
                                                 train_labels_path=train_labels_path, batch_size=64, split=True,
                                                 fract=0.2, evaluate_images_path=test_images_path,
                                                 evaluate_labels_path=test_labels_path)

# define dataset
train_ds = data_preprocessing.train_ds
test_ds = data_preprocessing.test_ds
evaluate_ds = data_preprocessing.evaluate_ds

# define model
model = LeNet()

# test model
# print(model.get_weights())

# # try to load pretrained model 
# path = './data/mnist_data/sample_weights.pkl'

# with open(path, 'rb') as f:
#     weights = pickle.load(f)

# model.set_pretrained_weights(weights, train_ds)
# new_weights = model.get_weights()
# print(new_weights[4])


tf_client = ClientAsyncFl(model=model, local_data_size=10000, train_ds=train_ds, test_ds=test_ds,
                          evaluate_ds=evaluate_ds)
tf_client.run()
