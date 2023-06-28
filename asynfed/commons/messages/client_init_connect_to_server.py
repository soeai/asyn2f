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


# class DataDesc(Message):
#     def __init__(self, name: str = "", desc: str = "", data_size: int = 10):
#         self.name = name
#         self.desc = desc
#         self.data_size = data_size


# class QoD(Message):
#     def __init__(self, schema: str = "", comment: str = "", value: float = 0.5):
#         self.schema = schema
#         self.comment = comment
#         self.value = value


class ClientInit(Message):
    def __init__(
        self,
        session_id: str = "",
        client_id: str = "",
        sys_info: SysInfo = SysInfo(),

        qod: float = 0.0,
        data_size: int = 10,
    ):
        super().__init__()
        self.session_id = session_id
        self.client_id = client_id
        self.sys_info = sys_info

        self.data_size = data_size
        self.qod = qod
