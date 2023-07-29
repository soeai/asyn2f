import os

from asynfed.common.utils.time_ultils import time_now
from asynfed.common.messages.client import SystemInfo


class Worker:
    """
    - This is the Worker class that contains information of worker.
    - Add more properties to this class.
    """

    def __init__(self, session_id: str, worker_id: str, sys_info: dict, data_size: int,
                 qod: float, cloud_access_key: str, cloud_secret_key: str) -> None:
        
        # Properties
        self.session_id = session_id
        self.worker_id = worker_id
        self.sys_info = SystemInfo(**sys_info)
        self.qod = qod
        self.data_size = data_size
        self.cloud_access_key: cloud_access_key
        self.cloud_secret_key: cloud_secret_key

        # the initial state
        self.last_ping = time_now()
        self.is_connected = True
        self.is_completed: bool = False
        self.alpha: float = None


        # the cloud storage path where the file is located
        self.global_version_used: int = 0
        self.remote_file_path: str = ""

        # 
        self.performance = 0.0
        self.loss = 0.0

        # a milestone for cleaning process to delete weight file 
        self.update_local_version_used: int = 0
        
        # property for the aggregating process
        # depend on algorithm strategy
        self.weight_array: list = None
        # info needed for aggregating
        # loss change from update time to update time



    def get_local_weight_file_path(self, local_model_root_folder: str):
        filename = self.remote_file_path.split(os.path.sep)[-1]
        return os.path.join(local_model_root_folder, self.worker_id, filename)
    
    def get_remote_weight_file_path(self):
        return self.remote_file_path

    def reset(self):
        """
        reset all properties 
        """
        self.n_update = 0
        self.current_version = 0
        self.alpha = 0.0
        self.performance = 0.0
        self.loss = 0.0
        self.is_completed = False
        self.weight_array = None


    def __str__(self):
        """
        Implement toString function here!
        """
        return f"Worker: {self.worker_id} | latest global version used {self.global_version_used} | qod: {self.qod} | datasize: {self.data_size} | performance: {self.performance} | loss: {self.loss}"
