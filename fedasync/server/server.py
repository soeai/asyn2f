from abc import abstractmethod, ABC
from time import sleep

from fedasync.server.server_queue_manager import ServerConsumer, ServerProducer
from fedasync.server.strategies import Strategy
from fedasync.server.worker_manager import WorkerManager
from fedasync.commons.utils import CloudStorageConnector
import threading
import os


# class DependenciesContainer:
#     worker_manager = None
#     queue_consumer = None
#     cloud_storage = None


class Server(ABC):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """

    def __init__(self, strategy: Strategy = None, t: int = 30) -> None:
        # Server variables
        self.t = t * 1000
        self.alpha: dict = {}
        self.current_version = 0

        # Server's dependencies
        self.cloud_storage: CloudStorageConnector = CloudStorageConnector()
        self.worker_manager: WorkerManager = WorkerManager()
        self.queue_consumer: ServerConsumer = ServerConsumer(self.cloud_storage, )
        self.queue_producer: ServerProducer = ServerProducer()
        self.strategy: Strategy = strategy

    def run(self):

        # create 1 thread to listen on the queue.
        consuming_thread = threading.Thread(target=self.queue_consumer.run, name="fedasync_server_consuming_thread")

        # run the consuming thread!.
        consuming_thread.start()

        while True:
            n_local_updates = self.worker_manager.get_n_local_update(self.current_version)
            if n_local_updates == 0:
                sleep(self.t)
            elif n_local_updates > 0:
                self.update()
        # the main thread will sleep for a t time.

    def stop_listening(self):
        pass

    def update(self):
        local_weights = self.worker_manager.get_all()
        self.strategy.aggregate(local_weights)
        pass

    @abstractmethod
    def is_stop_condition(self):
        return False
