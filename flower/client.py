
import os
import sys
import argparse
root = os.path.dirname(os.getcwd())
sys.path.append(root)

from experiment.cifar_dataset.client.centralized_resnet18.data_preprocessing import load_to_numpy_array
import flwr as fl
import tensorflow as tf
from experiment.cifar_dataset.client.data_preprocessing import preprocess_dataset
from experiment.cifar_dataset.client.resnet18 import Resnet18

def start_client(args):
    chunk = args.chunk
    if args.gpu is not None:
        try:
            tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[args.gpu], 'GPU')
            print("Using GPU: ", tf.config.list_physical_devices('GPU')[args.gpu])
        except:
            print("GPU not found, use CPU instead")
    else:
        print("Using CPU")
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
            model.fit(x_train, y_train, epochs=1, batch_size=32, steps_per_epoch=args.steps_per_epoch)
            return model.get_weights(), len(x_train), {}

        def evaluate(self, parameters, config):
            model.set_weights(parameters)
            loss, accuracy, _, _, _, _ = model.evaluate(x_test, y_test, batch_size=batch_size, return_dict=False)
            return loss, len(x_test), {"accuracy": accuracy}



    fl.client.start_numpy_client(server_address=args.address, client=CifarClient())
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Federated Learning Client")
        
    parser.add_argument("--gpu", type=int, default=None, help="Specify the GPU index")
    parser.add_argument("--chunk", type=int, default=1, help="Specify the chunk size")
    parser.add_argument("--address", type=str, default="0.0.0.0:8080", help="Specify the server address")
    parser.add_argument("--steps_per_epoch", type=int, default=50, help="Specify the number of steps per epoch")

    args = parser.parse_args()
    start_client(args)


