import logging
from typing import Dict, List
from .objects import Worker
from ..commons.messages.client_notify_model_to_server import ClientNotifyModelToServer

LOGGER = logging.getLogger(__name__)


class WorkerManager:
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

    def add_worker(self, worker: Worker) -> None:
        """Add a Worker to the worker_pools attribute.
        Args:
            worker (Worker): The Worker object to add.
        """
        LOGGER.info(f"New worker added, ID: {worker.worker_id}")
        self.worker_pool[worker.worker_id] = worker

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

    def add_local_update(self, message: ClientNotifyModelToServer):
        # update worker states with information from local worker.
        client_id = message.client_id
        self.worker_pool[client_id].current_version = message.global_model_version_used
        self.worker_pool[client_id].weight_file = message.weight_file
        self.worker_pool[client_id].loss = message.loss_value
        self.worker_pool[client_id].is_completed = True

    def update_worker_after_training(self):
        for worker in self.worker_pool:
            self.worker_pool[worker].is_completed = False

    def get_completed_workers(self) -> Dict:
        return {worker_id: self.worker_pool[worker_id] for worker_id in self.worker_pool if self.worker_pool[worker_id].is_completed == True}

    def get_worker_by_id(self, worker_id: str) -> Worker:
        return self.worker_pool[worker_id]

    def list_all_worker_session_id(self) -> List:
        return [self.worker_pool[worker_id].session_id for worker_id in self.worker_pool.keys()]
