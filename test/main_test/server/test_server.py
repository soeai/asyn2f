import sys
import os
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.extend([project_dir])
from asynfed.commons.conf import Config
from asynfed.server.server import Server
from asynfed.server.strategies import Strategy
from asynfed.server.strategies.AsynFL import AsynFL
from dotenv import load_dotenv
import os

load_dotenv()


Config.QUEUE_NAME = "server_queue"
Config.QUEUE_URL = "amqp://guest:guest@13.214.37.45:5672/%2F"
# Config.QUEUE_URL = "amqps://bxvrtbsf:RYNaloqSceK4YD59EQL44t-nYaWpVlnO@whale.rmq.cloudamqp.com/bxvrtbsf"
Config.TRAINING_EXCHANGE = "training_exchange"
Config.STORAGE_BUCKET_NAME = "fedasyn"
Config.STORAGE_ACCESS_KEY = os.getenv("access_key")
Config.STORAGE_SECRET_KEY = os.getenv("secret_key")

class FedAsyncServer(Server):
    def __init__(self, strategy: Strategy, t=30):
        super().__init__(strategy, t)

    def is_stop_condition(self):
        return False


strategy = AsynFL()

fedasync_server = FedAsyncServer(strategy)
fedasync_server.run()
