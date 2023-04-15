from .message import Message


class SysInfo(Message):
    def __init__(self, system: str = None, node: str = None, machine: str = None, mac_add: str = None):
        self.system = system
        self.node = node
        self.machine = machine
        self.mac_add = mac_add


class DataDesc(Message):
    def __init__(self, name: str = None, desc: str = None, data_size: str = None):
        self.name = name
        self.desc = desc
        self.data_size = data_size


class QoD(Message):
    def __init__(self, schema: str = None, comment: str = None):
        self.schema = schema
        self.comment = comment
        self.value = 0.0


class ClientInit(Message):
    def __init__(self, session_id: str = "", sys_info: SysInfo = SysInfo(), data_desc: DataDesc = DataDesc(),
                 qod: QoD = QoD()):
        super().__init__()
        self.session_id = session_id
        self.sys_info = sys_info
        self.data_desc = data_desc
        self.qod = qod
