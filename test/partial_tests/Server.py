from fedasync.commons.conf import GlobalConfig
from fedasync.server.server import Server
from fedasync.server.server_queue_connector import ServerQueueConnector

GlobalConfig.QUEUE_NAME = "server_queue"

test_Server = ServerQueueConnector()

test_Server.run_queue()
