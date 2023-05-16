from asynfed.commons.conf import Config
from asynfed.server.server import Server
from asynfed.server.server_queue_connector import ServerQueueConnector

Config.QUEUE_NAME = "server_queue"

test_Server = ServerQueueConnector()

test_Server.run_queue()
