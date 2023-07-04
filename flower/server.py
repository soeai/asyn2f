import os
import sys
root = os.path.dirname(os.getcwd())
sys.path.append(root)
import tensorflow as tf
import flwr as fl
from training_process.cifar_dataset.client.centralized_resnet18.data_preprocessing import load_to_numpy_array
import argparse
from training_process.cifar_dataset.client.resnet18 import Resnet18
from training_process.cifar_dataset.client.resnet18_5_chunks.data_preprocessing import preprocess_dataset


test_path = 'data/test_set.pickle'
learning_rate = 1e-1
epoch = 200
batch_size = 128
_, data_size = preprocess_dataset(test_path, batch_size=batch_size, training=False)
model = Resnet18(input_features=(32, 32, 3), 
                output_features=10,
                lr=learning_rate,
                decay_steps=epoch*data_size/batch_size)
model.build(input_shape=(None, 32, 32, 3))
# model.compile("adam", "sparse_categorical_crossentropy", metrics=["accuracy"])
model.compile("adam", "categorical_crossentropy", metrics=["accuracy"])

def get_evaluate_fn(model):
    """Return an evaluation function for server-side evaluation."""

    # Load data and model here to avoid the overhead of doing it in `evaluate` itself
    x_test, y_test = load_to_numpy_array(test_path)
    y_test = tf.keras.utils.to_categorical(y_test, 10)

    # The `evaluate` function will be called after every round
    def evaluate(server_round, parameters , config):
        model.set_weights(parameters)  
        loss, accuracy, _, _, _, _ = model.evaluate(x_test, y_test, return_dict=False)
        return loss, {"accuracy": accuracy}

    return evaluate


def start_server(args):
    strategy = fl.server.strategy.FedAvg(
        min_fit_clients=args.min_worker,
        evaluate_fn=get_evaluate_fn(model),
    )

    fl.server.start_server(
        server_address=args.address,
        config=fl.server.ServerConfig(args.num_rounds),
        strategy=strategy,
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Federated Learning Server")

    parser.add_argument("--address", type=str, default="0.0.0.0:8080", help="Specify the port number")
    parser.add_argument("--min_worker", type=int, default=2, help="Specify the minimum number of workers")
    parser.add_argument("--num_rounds", type=int, default=10, help="Specify the minimum number of workers")

    args = parser.parse_args()
    start_server(args)
