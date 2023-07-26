import os
import uuid
from typing import List
import re
from abc import ABC, abstractmethod
from time import sleep
import pickle
from typing import Dict
from asynfed.server.objects import Worker
from asynfed.server.server_boto3_storage_connector import ServerStorageBoto3

import logging
LOGGER = logging.getLogger(__name__)


class Strategy(ABC):
    """
    This here the Interface of strategy, follow the strategy design pattern.
    Any new strategy will follow this interface. 
    """
    def __init__(self):
        self.current_version: int = None
        self.model_id = str(uuid.uuid4())
        # change after each update time
        self.global_model_update_data_size = 0
        self.avg_loss = 0.0
        self.avg_qod = 0.0


    def get_current_global_model_filename(self):
        return f"{self.model_id}_v{self.current_version}.pkl"
    
    def get_new_global_model_filename(self):
        return f"{self.model_id}_v{self.current_version + 1}.pkl"

    # def update_new_global_model_info(self, )
    @abstractmethod
    def select_client(self, all_clients) -> List[str]:
        """ Implement the client selection logic by
        """
        pass

    @abstractmethod
    def aggregate(self, completed_workers, cloud_storage, local_storage_path):
        """Aggregate algorithm.
        """
        pass

    # @abstractmethod
    # def get_model_weights(self, file_path):
    #     """
    #     """
    #     pass

    def _get_valid_completed_workers(self, workers: Dict[str, Worker], cloud_storage: ServerStorageBoto3,
                                     local_model_root_folder: str) -> Dict[str, Worker]:
        valid_completed_workers = {}

        for w_id, worker in workers.items():
            remote_path = worker.get_remote_weight_file_path()
            LOGGER.info(f"{worker.worker_id} qod: {worker.qod}, loss: {worker.loss}, datasize : {worker.data_size}, weight file: {remote_path}")
            file_exists = cloud_storage.is_file_exists(file_path=remote_path)
            
            if file_exists:
                # valid_completed_workers[w_id] = worker
                LOGGER.info(f"{remote_path} exists in the cloud. Begin to download shortly")
                local_path = worker.get_weight_file_path(local_model_root_folder= local_model_root_folder)
                download_success = self._attempt_to_download(cloud_storage= cloud_storage, 
                                                             remote_file_path= remote_path, local_file_path= local_path)
                
                if download_success:
                    worker.weight_array =  self._get_model_weights(local_path)
                    valid_completed_workers[w_id] = worker

            else:
                LOGGER.info(f"worker {w_id}: weight file {remote_path} does not exist in the cloud. Remove {w_id} from aggregating process")

            LOGGER.info("*" * 20)

        return valid_completed_workers

    def _attempt_to_download(self, cloud_storage: ServerStorageBoto3, remote_file_path: str, local_file_path: str, n_attemps: int = 3) -> bool:
        for i in range(n_attemps):
            if cloud_storage.download(remote_file_path= remote_file_path, local_file_path= local_file_path, try_time=n_attemps):
                return True
            LOGGER.info(f"{i + 1} attempt: download model failed, retry in 5 seconds.")
            i += 1
            if i == n_attemps:
                LOGGER.info(f"Already try {n_attemps} time. Pass this client model: {remote_file_path}")
            sleep(5)

        return False

    def _get_model_weights(self, file_path):
        while not os.path.isfile(file_path):
            sleep(3)
        with open(file_path, "rb") as f:
            weights = pickle.load(f)
        return weights

    def _get_model_version(self, model_name: str):
        return int(re.search(r"v(\d+)", model_name.split("_")[1]).group(1))

