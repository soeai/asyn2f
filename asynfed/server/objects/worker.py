from asynfed.commons.conf import Config
from asynfed.commons.messages.client_init_connect_to_server import SysInfo


class Worker:
    """
    - This is the Worker class that contains information of worker.
    - Add more properties to this class.
    """

    def __init__(self, session_id: str, worker_id: str, sys_info: SysInfo = None, data_size: int = 10,
                 qod: float = 0.1) -> None:
        # Properties

        self.alpha = None
        self.session_id = session_id
        self.worker_id = worker_id
        self.sys_info = sys_info
        self.current_version = 0
        self.is_completed = False
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


    def get_weight_file_path(self):
        filename = self.weight_file.split('/')[-1]
        return f'{Config.TMP_LOCAL_MODEL_FOLDER}{self.worker_id}/{filename}'
    
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
