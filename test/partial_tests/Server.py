from fedasync.commons.conf import Config
from fedasync.server.server import Server
from fedasync.server.server_queue_connector import ServerQueueConnector

Config.QUEUE_NAME = "server_queue"

test_Server = ServerQueueConnector()

test_Server.run()
