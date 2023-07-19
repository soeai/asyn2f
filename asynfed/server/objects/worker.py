import os

from asynfed.commons.utils.time_ultils import time_now
from asynfed.commons.messages.client import SystemInfo


class Worker:
    """
    - This is the Worker class that contains information of worker.
    - Add more properties to this class.
    """

    def __init__(self, session_id: str, worker_id: str, sys_info: dict = SystemInfo().to_dict, data_size: int = 10,
                 qod: float = 0.1) -> None:
        
        # Properties
        self.is_completed: bool = False
        self.alpha = None
        self.session_id = session_id
        self.worker_id = worker_id
        self.sys_info = sys_info or SystemInfo().to_dict()
        self.current_version: int = 0

        self.update_local_version_used: int = 0
        
        self.access_key_id = None
        self.secret_key_id = None
        
        self.n_update = 0
        self.weight_file = ""
        
        self.performance = 0.0
        # info needed for aggregating
        self.qod = qod
        self.data_size = data_size
        # loss change from update time to update time
        self.loss = 0.0

        self.last_ping = time_now()
        self.is_connected = True


    def get_weight_file_path(self, local_model_root_folder: str):
        filename = self.weight_file.split(os.path.sep)[-1]
        return os.path.join(local_model_root_folder, self.worker_id, filename)
    
    def get_remote_weight_file_path(self):
        return self.weight_file

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


    def __str__(self):
        """
        Implement toString function here!
        """
        return f"Worker: {self.worker_id} | n_update: {self.n_update} | current_version: {self.current_version} | qod: {self.qod} | datasize: {self.data_size} | performance: {self.performance} | loss: {self.loss}"
