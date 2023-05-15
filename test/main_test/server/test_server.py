import sys
from fedasync.commons.conf import Config
from fedasync.server.server import Server
from fedasync.server.strategies import Strategy
from fedasync.server.strategies.AsynFL import AsynFL

print('Python %s on %s' % (sys.version, sys.platform))
sys.path.extend([''])

Config.QUEUE_NAME = "server_queue"
Config.QUEUE_URL = "amqp://guest:guest@13.214.37.45:5672/%2F"
Config.TRAINING_EXCHANGE = "training_exchange"
Config.STORAGE_BUCKET_NAME = "fedasyn"


class FedAsyncServer(Server):
    def __init__(self, strategy: Strategy, t=30):
        super().__init__(strategy, t)

    def is_stop_condition(self):
        return False


strategy = AsynFL()

fedasync_server = FedAsyncServer(strategy)
fedasync_server.run()
