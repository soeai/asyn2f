
import os
import sys
import argparse
from datetime import datetime
root = os.path.dirname(os.getcwd())
sys.path.append(root)

import flwr as fl
import tensorflow as tf
from data_preprocessing import *
from resnet18 import Resnet18
import logging

if not os.path.exists('client_logs'):
    os.makedirs('client_logs')
LOG_FORMAT = '%(levelname) -10s %(asctime)s %(name) -30s %(funcName) -35s %(lineno) -5d: %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    filename=f"client_logs/{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.log",
    filemode='a',
    datefmt='%H:%M:%S'
)
def start_client(args):

    if args.gpu is not None:
        try:
            tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[args.gpu], 'GPU')
            logging.info(f"Using GPU: {tf.config.list_physical_devices('GPU')[args.gpu]}")
        except:
            logging.info("GPU not found, use CPU instead")
    else:
        logging.info("Using CPU")

    chunk = args.chunk
    train_path = f'data/chunk_{chunk}.pickle'
    test_path = 'data/test_set.pickle'

    x_train, y_train, data_size = preprocess_dataset(train_path)
    x_test, y_test, _ = preprocess_dataset(test_path)

    logging.info(f'x_train shape: {x_train.shape} -- y_train shape: {y_train.shape} -- x_test shape: {x_test.shape} -- y_test shape: {y_test.shape}')

    
    datagen = get_datagen()
    datagen.fit(x_train)

    # HYPERPARAMETERS
    epoch = 200
    batch_size = args.batch_size

    learning_rate = 1e-1
    lambda_value = 5e-4
    decay_steps = epoch * data_size / batch_size


    # model
    model = Resnet18(num_classes= 10)
    # Set the learning rate and decay steps
    learning_rate_fn = tf.keras.experimental.CosineDecay(learning_rate, decay_steps=decay_steps)

    # Create the SGD optimizer with L2 regularization
    optimizer = tf.keras.optimizers.SGD(learning_rate=learning_rate_fn, momentum=0.9)
    regularizer = tf.keras.regularizers.l2(lambda_value)

    # Compile the model
    model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy'], 
                loss_weights=None, weighted_metrics=None, run_eagerly=None, 
                steps_per_execution=None)
    # Build the model
    model.build(input_shape=(None, 32, 32, 3))

    # Apply L2 regularization to applicable layers
    for layer in model.layers:
        if isinstance(layer, tf.keras.layers.Conv2D) or isinstance(layer, tf.keras.layers.Dense):
            layer.kernel_regularizer = regularizer
        if hasattr(layer, 'bias_regularizer') and layer.use_bias:
            layer.bias_regularizer = regularizer


    class CifarClient(fl.client.NumPyClient):
        def get_parameters(self, config):
            return model.get_weights()

        def fit(self, parameters, config):
            model.set_weights(parameters)
            model.fit(x_train, y_train, epochs=1, batch_size=batch_size, steps_per_epoch= data_size//batch_size)
            return model.get_weights(), len(x_train), {}

        def evaluate(self, parameters, config):
            model.set_weights(parameters)
            loss, accuracy = model.evaluate(x_test, y_test, batch_size=batch_size, return_dict=False)
            try:
                logging.info(f"round: {config['current_round']} -- loss: {loss} -- acc: {accuracy}")
            except:
                logging.info(f"loss: {loss} -- acc: {accuracy}")
            return loss, len(x_test), {"accuracy": accuracy}


    fl.client.start_numpy_client(server_address=args.address, client=CifarClient())
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Federated Learning Client")
        
    parser.add_argument("--gpu", type=int, default=0, help="Specify the GPU index")
    parser.add_argument("--chunk", type=int, default=1, help="Specify the chunk size")
    parser.add_argument("--address", type=str, default="0.0.0.0:8080", help="Specify the server address")
    parser.add_argument("--batch_size", type=int, default=128, help="Specify the batch size")

    args = parser.parse_args()
    start_client(args)


