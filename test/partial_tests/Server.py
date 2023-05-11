from fedasync.commons.conf import ServerConfig
from fedasync.server.server import Server
from fedasync.server.server_queue_connector import ServerQueueConnector

ServerConfig.QUEUE_NAME = "server_queue"

test_Server = ServerQueueConnector()

test_Server.run_queue()
