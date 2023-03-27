from abc import abstractmethod, ABC
from strategies import Strategy
from worker_manager import WorkerManager
from server_queue_manager import ServerQueueManager
from fedasync.commons.utils import CloudStorageConnector


class Server(ABC):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """

    def __init__(self, strategy: Strategy, t: int) -> None:
        # Server variables
        self.t = t
        self.alpha: dict = {}

        # Server's dependencies
        self.worker_manager: WorkerManager = WorkerManager()
        self.queue_manager: ServerQueueManager = ServerQueueManager()
        self.cloud_storage: CloudStorageConnector = CloudStorageConnector()
        self.strategy: Strategy = strategy

    def start_listening(self):
        pass

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
