import os
import uuid
from typing import List
import re
from abc import ABC, abstractmethod
from time import sleep
import pickle
from typing import Dict
from asynfed.server.objects import Worker
from asynfed.server.storage_connectors.boto3 import ServerStorageBoto3

import logging
LOGGER = logging.getLogger(__name__)


class Strategy(ABC):
    """
    This here the Interface of strategy, follow the strategy design pattern.
    Any new strategy will follow this interface. 
    """
    def __init__(self, model_name: str, file_extension: str = "pkl"):
        self.model_name = model_name
        self.file_extension = file_extension
        self.current_version: int = None
        # change after each update time
        self.global_model_update_data_size = 0
        self.avg_loss = 0.0
        self.avg_qod = 0.0


    def get_current_global_model_filename(self) -> str:
        # return f"{self.model_name}_v{self.current_version}.pkl"
        # "22.pkl"
        return f"{self.current_version}.{self.file_extension}"
    

    def get_new_global_model_filename(self) -> str:
        # "23.pkl"
        return f"{self.current_version + 1}.{self.file_extension}"


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


    def attempt_to_download(self, cloud_storage: ServerStorageBoto3, remote_file_path: str, local_file_path: str, n_attemps: int = 3) -> bool:
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
    
    

    def extract_model_version(self, folder_path: str) -> int:
        # Use os.path to split the path into components
        _, filename = os.path.split(folder_path)
        
        # Search for any sequence of digits (\d+) that comes directly before the file extension
        # match = re.search(rf'(\d+){re.escape(self.file_extension)}', filename)
        match = re.search(r'(\d+)\.', filename)  # Look for digits followed by a dot

        # If a match was found, convert it to int and return it
        if match:
            return int(match.group(1))
        
        # If no match was found, return None
        return None
