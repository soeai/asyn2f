from .message import Message


class ClientInit(Message):
    def __init__(self, message):
        self.sessionid = ""
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