import sys
import os
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.extend([project_dir])
from fedasync.commons.conf import Config
from fedasync.server.server import Server
from fedasync.server.strategies import Strategy
from fedasync.server.strategies.AsynFL import AsynFL


Config.QUEUE_NAME = "server_queue"
Config.QUEUE_URL = "amqps://bxvrtbsf:RYNaloqSceK4YD59EQL44t-nYaWpVlnO@whale.rmq.cloudamqp.com/bxvrtbsf"
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
