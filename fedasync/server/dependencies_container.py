class DependenciesContainer:
    def __init__(self, worker_manager=None, queue_consumer=None, queue_producer=None, cloud_storage=None, server=None, strategy=None):
        from fedasync.server import Server
        from fedasync.server.server_queue_manager import ServerConsumer, ServerProducer
        from fedasync.server.strategies import Strategy
        from fedasync.server.worker_manager import WorkerManager
        from fedasync.server.server_storage_connector import ServerStorage

        self.worker_manager: WorkerManager = worker_manager
        self.queue_consumer: ServerConsumer = queue_consumer
        self.queue_producer: ServerProducer = queue_producer
        self.cloud_storage: ServerStorage = cloud_storage
        self.server: Server = server
        self.strategy: Strategy = strategy
