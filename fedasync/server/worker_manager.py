import logging
from typing import List, Dict
from .objects import Worker
from ..commons.messages.client_notify_model_to_server import ClientNotifyModelToServer
from ..commons.messages.message import Message

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

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

        # all worker information
        self.worker_pool: Dict[str, Worker] = {}

        # save history state by version.
        self.history_state: Dict[int, Dict[str, Worker]] = {}

        # save local weights by version
        self.weight_pool: Dict[int, Dict] = {}

    def add_worker(self, worker: Worker) -> None:
        """Add a Worker to the worker_pools attribute.
        Args:
            worker (Worker): The Worker object to add.
        """
        LOGGER.info("Add worker")

    def total(self) -> int:
        """Get the total number of Workers.
        Returns:
            int: The number of Workers in the worker_pools attribute.
        """
        return len(self.worker_pool)

    def get_all(self) -> Dict[str, Worker]:
        """Get all Workers from the worker_pools attribute.
        Returns:
           Dict[str, Worker]: A dictionary of all Worker objects in the
               worker_pools attribute, keyed by Worker id.
        """
        return self.worker_pool

    def get_n_local_update(self, global_model_version):
        LOGGER.info("Get n local updates")
        return self.total()

    def add_local_update(self, message: ClientNotifyModelToServer):
        pass
