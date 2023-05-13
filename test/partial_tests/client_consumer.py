from fedasync.client.client import Client
from fedasync.commons.conf import GlobalConfig

GlobalConfig.QUEUE_NAME = "client_queue"
client_consumer = Client()
client_consumer.run_queue()
