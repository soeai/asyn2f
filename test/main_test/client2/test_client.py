
import sys

sys.path.extend(['/Users/tleq/PycharmProjects/AsynFL'])


from fedasync.commons.conf import ClientConfig
from fedasync.client.client_tensorflow import ClientTensorflow
from fedasync.client.tensorflow_examples.mnist.lenet_model import LeNet
from fedasync.client.tensorflow_examples.mnist.data_preprocessing import TensorflowDataPreprocessing
# import tensorflow as tf
import pickle


# Preprocessing data
# mnist dataset
# Set the file paths for the MNIST digit dataset files
train_images_path = '../data/mnist_data/train-images-idx3-ubyte.gz'
train_labels_path = '../data/mnist_data/train-labels-idx1-ubyte.gz'
test_images_path = '../data/mnist_data/t10k-images-idx3-ubyte.gz'
test_labels_path = '../data/mnist_data/t10k-labels-idx1-ubyte.gz'

ClientConfig.TMP_LOCAL_MODEL_FOLDER = 'data/client/local_weights/'
ClientConfig.TMP_GLOBAL_MODEL_FOLDER = 'data/client/global_weights/'


# preprocessing data to be ready for low level tensorflow training process
data_preprocessing = TensorflowDataPreprocessing(train_images_path = train_images_path, train_labels_path= train_labels_path, batch_size= 64, split= True, fract= 0.2, evaluate_images_path= test_images_path, evaluate_labels_path= test_labels_path)
print(type(data_preprocessing.train_ds))
print(type(data_preprocessing.test_ds))
print(type(data_preprocessing.evaluate_ds))

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


tf_client = ClientTensorflow(model=model, local_data_size=10000, train_ds= train_ds, test_ds= test_ds, evaluate_ds= evaluate_ds)
tf_client.run()
