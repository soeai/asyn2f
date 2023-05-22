from asynfed.client.client import Client
from asynfed.commons.conf import Config

Config.QUEUE_NAME = "client_queue"
client_consumer = Client()
client_consumer.run_queue()
