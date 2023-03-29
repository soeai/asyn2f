from abc import abstractmethod, ABC
from time import sleep

from fedasync.server import DependenciesContainer
from fedasync.server.server_queue_manager import ServerConsumer, ServerProducer
from fedasync.server.strategies import Strategy
from fedasync.server.worker_manager import WorkerManager
from fedasync.commons.utils import CloudStorageConnector
import threading

lock = threading.Lock()


class Server(ABC):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """

    def __init__(self, strategy: Strategy = None, t: int = 30) -> None:
        # Server variables
        self.t = t * 1000
        self.alpha: dict = {}
        self.strategy = strategy

        # Server's self.dependencies
        self.dependencies = DependenciesContainer()
        self.dependencies.cloud_storage = CloudStorageConnector()
        self.dependencies.worker_manager = WorkerManager()
        self.dependencies.queue_consumer = ServerConsumer(self.dependencies)
        self.dependencies.queue_producer = ServerProducer()
        self.dependencies.server = self

    def run(self):

        total_online_worker = self.dependencies.worker_manager.get_all()

        # create 1 thread to listen on the queue.
        consuming_thread = threading.Thread(target=self.dependencies.queue_consumer.run,
                                            name="fedasync_server_consuming_thread")

        # run the consuming thread!.
        consuming_thread.start()

        while True:
            with lock:
                n_local_updates = self.dependencies.worker_manager.get_n_local_update(self.strategy.current_version)

            if n_local_updates == 0:
                sleep(self.t)
            elif n_local_updates > 0:
                self.update()
            if self.is_stop_condition():
                self.stop_listening()
                break

    def stop_listening(self):
        with lock:
            self.dependencies.queue_consumer.stop()

    def update(self):
        with lock:
            local_weights = self.dependencies.worker_manager.get_all()
        self.strategy.aggregate(local_weights)

    @abstractmethod
    def is_stop_condition(self):
        return False
