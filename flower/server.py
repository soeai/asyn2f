import os
import sys
root = os.path.dirname(os.getcwd())
sys.path.append(root)
from datetime import datetime
import flwr as fl
import argparse
from flower.resnet18 import Resnet18
from flower.data_preprocessing import preprocess_dataset
import logging
import numpy as np

if not os.path.exists('server_logs'):
    os.makedirs('server_logs')
if not os.path.exists('server_weights'):
    os.makedirs('server_weights')
LOG_FORMAT = '%(levelname) -10s %(asctime)s %(name) -30s %(funcName) -35s %(lineno) -5d: %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    filename=f"server_logs/{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.log",
    filemode='a',
    datefmt='%H:%M:%S'
)

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

def fit_config(server_round: int):
    """Return training configuration dict for each round."""
    config = {
        "current_round": server_round,
    }
    return config

def get_evaluate_fn(model):
    """Return an evaluation function for server-side evaluation."""
    # The `evaluate` function will be called after every round
    def evaluate(server_round, parameters , config):
        model.set_weights(parameters)  
        loss, accuracy = model.evaluate(x_test, y_test, return_dict=False)
        logging.info(f"Round {server_round} | Loss: {loss} | Accuracy: {accuracy}")
        return loss, {"accuracy": accuracy}
    return evaluate


def start_server(args):
    class AggregateCustomMetricStrategy(fl.server.strategy.FedAvg):
        def aggregate_fit( self, server_round, results, failures):

            # Call aggregate_fit from base class (FedAvg) to aggregate parameters and metrics
            aggregated_parameters, aggregated_metrics = super().aggregate_fit(server_round, results, failures)

            if aggregated_parameters is not None:
                # Convert `Parameters` to `List[np.ndarray]`
                aggregated_ndarrays: List[np.ndarray] = fl.common.parameters_to_ndarrays(aggregated_parameters)

                # Save aggregated_ndarrays
                logging.info(f"Saving round {server_round} aggregated_ndarrays...")
                np.savez(f"server_weights/round-{server_round}-weights.npz", *aggregated_ndarrays)

            return aggregated_parameters, aggregated_metrics

        def aggregate_evaluate(self, server_round, results, failures,):
            """Aggregate evaluation accuracy using weighted average."""

            if not results:
                return None, {}

            # Call aggregate_evaluate from base class (FedAvg) to aggregate loss and metrics
            aggregated_loss, aggregated_metrics = super().aggregate_evaluate(server_round, results, failures)

            # Weigh accuracy of each client by number of examples used
            accuracies = [r.metrics["accuracy"] * r.num_examples for _, r in results]
            examples = [r.num_examples for _, r in results]

            # Aggregate and print custom metric
            aggregated_accuracy = sum(accuracies) / sum(examples)
            logging.info(f"Round {server_round} accuracy aggregated from client results: {aggregated_accuracy}")

            # Return aggregated loss and metrics (i.e., aggregated accuracy)
            return aggregated_loss, {"accuracy": aggregated_accuracy}
    strategy = AggregateCustomMetricStrategy(
        # min_fit_clients=args.min_worker,
        # min_evaluate_clients=args.min_worker,
        min_available_clients=args.min_worker,
        evaluate_fn=get_evaluate_fn(model),
        on_fit_config_fn=fit_config,
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
