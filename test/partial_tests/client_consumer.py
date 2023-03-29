from fedasync.client.client_queue_manager import ClientConsumer
from fedasync.commons.conf import Config

Config.QUEUE_NAME = "client_queue"
client_consumer = ClientConsumer()
client_consumer.run()
