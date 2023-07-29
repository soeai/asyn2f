import logging
from typing import Dict, List

from asynfed.server.objects import Worker
from asynfed.common.messages.client import ClientModelUpdate
import asynfed.common.utils.time_ultils as time_utils

LOGGER = logging.getLogger(__name__)


from threading import Lock

class WorkerManager:
    def __init__(self) -> None:
        # ...
        self.worker_pool: Dict[str, Worker] = {}
        self.history_state: Dict[int, Dict[str, Worker]] = {}
        self.lock = Lock()  # Initialize a lock

    def add_worker(self, worker: Worker) -> None:
        with self.lock:
            self.worker_pool[worker.worker_id] = worker

    def get_all_worker(self) -> Dict [str, Worker]:
        with self.lock:
            return self.worker_pool

    def add_local_update(self, client_id: str, client_model_update: ClientModelUpdate):
        with self.lock:
            worker: Worker = self.worker_pool[client_id]
            worker.is_completed = True
            worker.remote_file_path = client_model_update.storage_path
            worker.global_version_used = client_model_update.global_version_used
            worker.loss = client_model_update.loss

    def get_completed_workers(self) -> Dict:
        with self.lock:
            return {worker_id: self.worker_pool[worker_id] for worker_id in self.worker_pool if self.worker_pool[worker_id].is_completed == True}

    def get_worker_by_id(self, worker_id: str) -> Worker:
        with self.lock:
            return self.worker_pool[worker_id]

    def list_sessions(self) -> List:
        with self.lock:
            return [self.worker_pool[worker_id].session_id for worker_id in self.worker_pool.keys()]

    def list_connected_workers(self) -> List[str]:
        with self.lock:
            return [worker_id for worker_id in self.worker_pool.keys() if self.worker_pool[worker_id].is_connected == True]

    def get_num_connected_workers(self) -> int:
        with self.lock:
            return len(self.list_connected_workers())

    def get_connected_workers(self) -> Dict[str, Worker]:
        with self.lock:
            return {worker_id: self.worker_pool[worker_id] for worker_id in self.worker_pool if self.worker_pool[worker_id].is_connected == True}

    def check_connected_workers_complete_status(self) -> bool:
        with self.lock:
            connected_workers = self.get_connected_workers()
            for w_id, worker in connected_workers.items():
                if "tester" not in w_id:
                    if not worker.is_completed:
                        return False
            return True

    def reset_all_workers_training_state(self):
        with self.lock:
            for w_id, worker in self.worker_pool.items():
                worker.reset()

    def update_worker_connections(self) -> None:
        with self.lock:
            for worker_id in self.worker_pool.keys():
                if time_utils.time_diff(time_utils.time_now(), self.worker_pool[worker_id].last_ping) < 60:
                    self.worker_pool[worker_id].is_connected = True
                else:
                    self.worker_pool[worker_id].is_connected = False

    def update_worker_last_ping(self, worker_id):
        with self.lock:
            self.worker_pool[worker_id].last_ping = time_utils.time_now()


