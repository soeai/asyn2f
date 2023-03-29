from fedasync.commons.conf import Config
from fedasync.server.server import Server
from fedasync.server.server_queue_manager import ServerConsumer

Config.QUEUE_NAME = "server_queue"

test_Server = ServerConsumer()

test_Server.run()
