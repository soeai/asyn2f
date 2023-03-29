from typing import List, Dict

from fedasync.commons.messages.client_init_connect_to_server import SysInfo, DataDesc, QoD


class Worker:
    """
    - This is the Worker class that contains information of worker.
    - Add more properties to this class.
    """

    def __init__(self, id: str, sys_info: SysInfo = None, data_desc: DataDesc = None, qod: QoD = None) -> None:
        # Properties
        self.id: str = id
        self.sys_info = sys_info
        self.data_desc = data_desc
        self.qod = qod

        self.n_update = 0
        self.current_version = 0
        self.alpha = {
        }
        self.performance = {
        }
        self.loss = {
        }

    def reset(self):
        """
        reset all properties 
        """

    def __str__(self):
        """
        Implement toString function here!
        """

