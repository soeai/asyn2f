import os
import sys
root = os.path.dirname(os.getcwd())
sys.path.append(root)
import tensorflow as tf
import flwr as fl
from experiment.cifar_dataset.client.centralized_resnet18.data_preprocessing import load_to_numpy_array
import argparse
from experiment.cifar_dataset.client.resnet18 import Resnet18
from experiment.cifar_dataset.client.data_preprocessing import preprocess_dataset


test_path = 'data/test_set.pickle'
x_test, y_test, data_size = preprocess_dataset(test_path)

epoch = 200
batch_size = 128
learning_rate = 1e-1
lambda_value = 5e-4

# model
# because we don't need to train on server
# just build a simple model
model = Resnet18(num_classes= 10)
# Compile the model
model.build(input_shape=(None, 32, 32, 3))
# model.compile("adam", "sparse_categorical_crossentropy", metrics=["accuracy"])
model.compile("adam", "categorical_crossentropy", metrics=["accuracy"])


def get_evaluate_fn(model):
    """Return an evaluation function for server-side evaluation."""
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
    parser.add_argument("--num_rounds", type=int, default=200, help="Specify the number of iterations")

    args = parser.parse_args()
    start_server(args)
