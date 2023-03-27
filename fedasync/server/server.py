from abc import abstractmethod, ABC

from fedasync.server.server_queue_manager import ServerConsumer, ServerProducer
from strategies import Strategy
from worker_manager import WorkerManager
from fedasync.commons.utils import CloudStorageConnector
import threading
import os


class Server(ABC):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """

    def __init__(self, strategy: Strategy, t: int) -> None:
        # Server variables
        self.t = t
        self.alpha: dict = {}
        self.n_local_updates = 0

        # Server's dependencies
        self.worker_manager: WorkerManager = WorkerManager()
        self.queue_consumer: ServerConsumer = ServerConsumer()
        self.queue_producer: ServerProducer = ServerProducer()
        self.cloud_storage: CloudStorageConnector = CloudStorageConnector()
        self.strategy: Strategy = strategy

    def run(self):
        # create 1 thread to listen on the queue.
        consuming_thread = threading.Thread(target=self.queue_consumer.run, name="fedasync_server-consuming-thread")

        # run the consuming thread!.
        consuming_thread.start()

        # the main thread will sleep for a t time.

    def stop_listening(self):
        pass

    def update(self):
        pass

    def evaluate(self):
        pass

    def event_handler(self):
        pass

    def get_message(self):
        pass

    @abstractmethod
    def is_stop_condition(self):
        return False
