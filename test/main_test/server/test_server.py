import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))))
from asynfed.commons.conf import Config
from asynfed.server.server import Server
from asynfed.server.strategies import Strategy
from asynfed.server.strategies.AsynFL import AsynFL
from dotenv import load_dotenv

load_dotenv()

Config.QUEUE_URL = "amqp://guest:guest@13.214.37.45:5672/%2F"
# Config.QUEUE_URL = "amqps://bxvrtbsf:RYNaloqSceK4YD59EQL44t-nYaWpVlnO@whale.rmq.cloudamqp.com/bxvrtbsf"
Config.STORAGE_ACCESS_KEY = os.getenv("access_key")
Config.STORAGE_SECRET_KEY = os.getenv("secret_key")


strategy = AsynFL()

fedasync_server = Server(strategy, t=40)
fedasync_server.run()
