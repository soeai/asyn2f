from typing import List, Dict
from .objects import Worker
    
    




class WorkerManager:
    
    """
    Implement methods that manage Workers here!
    """

    def __init__(self) -> None:
        """
            Initialize a WorkerManager object.
            The Worker_pools attribute is a dictionary of Worker objects,keyed by Worker id.
            The history_state attribute is a dictionary that maps epoch numbers
            to dictionaries of Worker objects, keyed by Worker id.
        """
        self.worker_pools: Dict[str, Worker] = {}
        self.history_state: Dict[int, Dict[str, Worker]] = {}
        
    def add_worker(self, Worker: Worker) -> None:
        """Add a Worker to the worker_pools attribute.
        Args:
            Worker (Worker): The Worker object to add.
        """
    
    def total(self):
        """Get the total number of Workers.
        Returns:
            int: The number of Workers in the worker_pools attribute.
        """
        return len(self.worker_pools)
    
    def get_all(self) -> Dict[str, Worker]:
        """Get all Workers from the worker_pools attribute.
        Returns:
           Dict[str, Worker]: A dictionary of all Worker objects in the
               worker_pools attribute, keyed by Worker id.
        """
        return self.worker_pools
    
    