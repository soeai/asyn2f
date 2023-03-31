from fedasync.client.queue_manager import ClientQueueConnector
from fedasync.commons.conf import Config

Config.QUEUE_NAME = "client_queue"
client_consumer = ClientQueueConnector()
client_consumer.run()
