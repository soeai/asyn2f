
from abc import abstractmethod, ABC
from strategies import Strategy
from worker_manager import WorkerManager
from queue_manager import QueueManager
from commons.utils import CloudStorageConnector
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection




class Server(ABC):
    
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """
    
    def __init__(self, strategy : Strategy, queue_connection: BlockingConnection, t: int) -> None:
        
        # Server variables
        self.queue_connection = queue_connection
        self.t = t
        self.alpha : dict = {}
        
        
        # Server's dependencies
        self.worker_manager : WorkerManager = WorkerManager()
        self.queue_manager : QueueManager = QueueManager(queue_connection=queue_connection)
        self.cloud_storage : CloudStorageConnector = CloudStorageConnector()
        self.strategy : Strategy = strategy
        
    
    
    def start_listening(self):
        pass
    
    def stop_listening(self):
        pass
    
    def update(self):
        pass
    
    def evaluate(self):
        pass
    
    @abstractmethod
    def is_stop_condition(self):
        return False