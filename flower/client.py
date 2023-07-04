
import os
import sys
root = os.path.dirname(os.getcwd())
sys.path.append(root)

from training_process.cifar_dataset.client.centralized_resnet18.data_preprocessing import load_to_numpy_array
import flwr as fl
import tensorflow as tf
from training_process.cifar_dataset.client.resnet18_5_chunks.data_preprocessing import preprocess_dataset
from training_process.cifar_dataset.client.resnet18 import Resnet18


args = sys.argv
chunk = int(args[1])

# HYPERPARAMETERS
learning_rate = 1e-1
epoch = 200
batch_size = 128


test_path = 'data/test_set.pickle'
train_path = f'data/chunk_{chunk}.pickle'
train_ds, data_size = preprocess_dataset(train_path, batch_size=128, training=True)

print('data size:', data_size)
x_train, y_train = load_to_numpy_array(train_path)
x_test, y_test = load_to_numpy_array(test_path)

y_train = tf.keras.utils.to_categorical(y_train, 10)
y_test = tf.keras.utils.to_categorical(y_test, 10)


print('x_train shape:', x_train.shape, 'y_train shape:', y_train.shape, 'x_test shape:', x_test.shape, 'y_test shape:', y_test.shape)
model = Resnet18(input_features= (32, 32, 3), 
                 output_features= 10,
                 lr=learning_rate,
                 decay_steps=epoch*data_size/batch_size)
model.build(input_shape=(None, 32, 32, 3))
# model.compile("adam", "sparse_categorical_crossentropy", metrics=["accuracy"])
model.compile("adam", "categorical_crossentropy", metrics=["accuracy"])

class CifarClient(fl.client.NumPyClient):
    def get_parameters(self, config):
        return model.get_weights()

    def fit(self, parameters, config):
        model.set_weights(parameters)
        model.fit(x_train, y_train, epochs=1, batch_size=32, steps_per_epoch=10)
        return model.get_weights(), len(x_train), {}

    def evaluate(self, parameters, config):
        model.set_weights(parameters)
        loss, accuracy, _, _, _, _ = model.evaluate(x_test, y_test, batch_size=batch_size, return_dict=False)
        return loss, len(x_test), {"accuracy": accuracy}



fl.client.start_numpy_client(server_address="localhost:8080", client=CifarClient())
