from fedasync.client.client import ClientConsumer
from fedasync.commons.conf import Config

Config.QUEUE_NAME = "client_queue"
client_consumer = ClientConsumer()
client_consumer.run()
