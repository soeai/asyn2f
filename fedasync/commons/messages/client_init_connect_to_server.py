from typing import Optional, Dict, Union

from .message import Message
import uuid

class ClientInit(Message):
    def __init__(self, message: Union[str, Dict] = None):
        self.sessionid = str(uuid.uuid4())
        self.sys_info: SysInfo = SysInfo()
        self.data_desc: DataDesc = DataDesc()
        self.qod: QoD = QoD()

        self.deserialize(message)


class SysInfo(Message):
    def __init__(self):
        self.system = ""
        self.node = ""
        self.machine = ""
        self.mac_add = ""


class DataDesc(Message):
    def __init__(self):
        self.name = ""
        self.desc = ""
        self.data_size = ""


class QoD(Message):
    def __init__(self):
        self.schema = ""
        self.comment = ""
