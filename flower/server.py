import flwr as fl
import argparse


def start_server(args):
    strategy = fl.server.strategy.FedAvg(
        min_fit_clients=args.min_worker,
    )

    fl.server.start_server(
        server_address=args.address,
        config=fl.server.ServerConfig(args.num_rounds),
        strategy=strategy,
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Federated Learning Server")

    parser.add_argument("--address", type=str, default="localhost:8080", help="Specify the port number")
    parser.add_argument("--min_worker", type=int, default=2, help="Specify the minimum number of workers")
    parser.add_argument("--num_rounds", type=int, default=10, help="Specify the minimum number of workers")

    args = parser.parse_args()
    start_server(args)
