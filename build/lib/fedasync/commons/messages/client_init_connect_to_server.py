from .message import Message


class SysInfo(Message):
    def __init__(
        self,
        system: str = "",
        node: str = "",
        machine: str = "",
        mac_add: str = "",
    ):
        self.system = system
        self.node = node
        self.machine = machine
        self.mac_add = mac_add


class DataDesc(Message):
    def __init__(self, name: str = "", desc: str = "", data_size: str = ""):
        self.name = name
        self.desc = desc
        self.data_size = data_size


class QoD(Message):
    def __init__(self, schema: str = "", comment: str = ""):
        self.schema = schema
        self.comment = comment
        self.value = 0.0


class ClientInit(Message):
    def __init__(
        self,
        client_identifier: str = "",
        session_id: str = "",
        client_id: str = "",
        sys_info: SysInfo = SysInfo(),
        data_desc: DataDesc = DataDesc(),
        qod: QoD = QoD(),
    ):
        super().__init__()
        self.client_identifier = client_identifier
        self.session_id = session_id
        self.client_id = client_id
        self.sys_info = sys_info
        self.data_desc = data_desc
        self.qod = qod