# from ...client_tensorflow import ClientTensorflow
# from ....client.client_tensorflow import ClientTensorflow
# from tensorflow_data_preprocessing import TensorflowDataPreprocessing

# from tensorflow_data_preprocessing import TensorflowDataPreprocessing
# from tensorflow_model import LeNet

import sys
print('Python %s on %s' % (sys.version, sys.platform))
sys.path.extend(['/home/vtn_ubuntu/ttu/spring23/working_project/AsynFL'])

from test.tensorflow_examples.mnist.data_preprocessing import TensorflowDataPreprocessing
from test.tensorflow_examples.mnist.lenet_model import LeNet

import pickle

# Set the file paths for the MNIST digit dataset files
train_images_path = 'mnist_data/train-images-idx3-ubyte.gz'
train_labels_path = 'mnist_data/train-labels-idx1-ubyte.gz'
test_images_path = 'mnist_data/t10k-images-idx3-ubyte.gz'
test_labels_path = 'mnist_data/t10k-labels-idx1-ubyte.gz'

# preprocessing data to be ready for low level tensorflow training process
data_preprocessing = TensorflowDataPreprocessing(train_images_path = train_images_path, train_labels_path= train_labels_path, batch_size= 64, split= True, fract= 0.2, evaluate_images_path= test_images_path, evaluate_labels_path= test_labels_path)
print(type(data_preprocessing.train_ds))
print(type(data_preprocessing.test_ds))
print(type(data_preprocessing.evaluate_ds))

# define dataset
train_ds = data_preprocessing.train_ds
test_ds = data_preprocessing.test_ds
evaluate_ds = data_preprocessing.evaluate_ds

# createa an instance of the model
model = LeNet()
print(model.get_weights())

# try to load pretrained model 
# mismatch can happen wiwth the number of layers between the initialized model vs pretrained model
path = 'stimulate_distributed_system/result/local/epoch1/worker1_10000_0_1.pkl'

with open(path, 'rb') as f:
    weights = pickle.load(f)
model.set_pretrained_weights(weights, train_ds)
new_weights = model.get_weights()
print(new_weights[4])

