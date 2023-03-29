from fedasync.server.server import Server
from fedasync.server.server__cloud_storage import ServerCloudStorage
from fedasync.server.server_queue_manager import ServerConsumer, ServerProducer
from fedasync.server.worker_manager import WorkerManager


class DependenciesContainer:
    def __init__(self):
        self.worker_manager: WorkerManager = None
        self.queue_consumer: ServerConsumer = None
        self.queue_producer: ServerProducer = None
        self.cloud_storage: ServerCloudStorage = None
        self.server: Server = None
