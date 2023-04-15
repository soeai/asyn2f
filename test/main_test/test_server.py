import sys
print('Python %s on %s' % (sys.version, sys.platform))
sys.path.extend(['/home/vtn_ubuntu/ttu/spring23/working_project/AsynFL'])


from fedasync.commons.conf import Config
from fedasync.server.server import Server
from fedasync.server.strategies import Strategy
from fedasync.server.strategies.AsynFL import AsynFL

Config.QUEUE_NAME = "server_queue"
Config.QUEUE_URL = "amqp://guest:guest@localhost:5672/%2F"
Config.TRAINING_EXCHANGE = "training_exchange"
Config.TMP_GLOBAL_MODEL_FOLDER = "./data/global_weights/"


class FedAsyncServer(Server):
    def __init__(self, strategy: Strategy, t=40):
        super().__init__(strategy, t)

    def is_stop_condition(self):
        return False


strategy = AsynFL()

fedasync_server = FedAsyncServer(strategy)
fedasync_server.run()
