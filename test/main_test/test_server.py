from fedasync.commons.conf import Config
from fedasync.server.server import Server
from fedasync.server.strategies import Strategy
from fedasync.server.strategies.AsyncFL import AsyncFL

Config.QUEUE_NAME = "server_queue"
Config.QUEUE_URL = "amqp://guest:guest@localhost:5672/%2F"
Config.TRAINING_EXCHANGE = "training_exchange"
Config.TMP_MODEL_FOLDER = "./tmp_folder"


class FedAsyncServer(Server):
    def __init__(self, strategy: Strategy):
        super().__init__(strategy)

    def is_stop_condition(self):
        return False


strategy = AsyncFL()
strategy.current_version = 0

fedasync_server = FedAsyncServer(strategy)
fedasync_server.run()
