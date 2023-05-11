import sys
print('Python %s on %s' % (sys.version, sys.platform))
sys.path.extend(['/home/vtn_ubuntu/ttu/spring23/working_project/AsynFL'])


from fedasync.commons.conf import ServerConfig
from fedasync.server.server import Server
from fedasync.server.strategies import Strategy
from fedasync.server.strategies.AsynFL import AsynFL

# sys.path.extend(['/home/vtn_ubuntu/ttu/spring23/working_project/AsynFL/fedasync'])


ServerConfig.QUEUE_NAME = "server_queue"
ServerConfig.QUEUE_URL = "amqp://guest:guest@localhost:5672/%2F"
ServerConfig.TRAINING_EXCHANGE = "training_exchange"


class FedAsyncServer(Server):
    def __init__(self, strategy: Strategy, t=30):
        super().__init__(strategy, t)

    def is_stop_condition(self):
        return False


strategy = AsynFL()

fedasync_server = FedAsyncServer(strategy)
fedasync_server.server_access_key = 'AKIA2X4RVJV36KLB3BXF'
fedasync_server.server_secret_key = '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'
fedasync_server.run()
