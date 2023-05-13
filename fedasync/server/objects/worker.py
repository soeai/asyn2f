from fedasync.commons.conf import GlobalConfig
from fedasync.commons.messages.client_init_connect_to_server import SysInfo, DataDesc, QoD


class Worker:
    """
    - This is the Worker class that contains information of worker.
    - Add more properties to this class.
    """

    def __init__(self, worker_id: str, sys_info: SysInfo = None, data_desc: DataDesc = None, qod: QoD = None) -> None:
        # Properties
        self.worker_id = worker_id
        self.sys_info = sys_info
        self.data_desc = data_desc
        self.qod = qod
        self.weight_file = ""
        self.n_update = 0
        self.current_version = 0
        self.alpha = 0.0
        self.batch_size = 0
        self.performance = 0.0
        self.loss = 0.0
        self.is_completed = False
        self.access_key_id = None

    def get_weight_file_path(self):
        filename = self.weight_file.split('/')[-1]
        return f'{GlobalConfig.TMP_LOCAL_MODEL_FOLDER}{filename}'

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
        return f"Worker: {self.worker_id} | n_update: {self.n_update} | current_version: {self.current_version} | alpha: {self.alpha} | performance: {self.performance} | loss: {self.loss}"

