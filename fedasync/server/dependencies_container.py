class DependenciesContainer:
    def __init__(self):
        from fedasync.server import Server
        from fedasync.server.server_queue_manager import ServerConsumer, ServerProducer
        from fedasync.server.strategies import Strategy
        from fedasync.server.worker_manager import WorkerManager
        from fedasync.commons.utils import CloudStorageConnector

        self.worker_manager: WorkerManager = None
        self.queue_consumer: ServerConsumer = None
        self.queue_producer: ServerProducer = None
        self.cloud_storage: CloudStorageConnector = None
        self.server: Server = None
        self.strategy: Strategy = None
