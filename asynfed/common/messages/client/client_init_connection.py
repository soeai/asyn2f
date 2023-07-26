
from asynfed.common.messages import MessageObject

class SystemInfo(MessageObject):
    def __init__(self, cpu='x86_64', gpu='NVIDIA GTX 1080 Ti', ram='16GB', disk='80GB') -> None:
        self.cpu = cpu
        self.ram = ram 
        self.gpu = gpu
        self.disk = disk



class DataDescription(MessageObject):
    def __init__(self, size: int = 10, qod: float = 0.5) -> None:
        self.size = size
        self.qod = qod


class ClientInitConnection(MessageObject):
    def __init__(self, role: str = "trainer", system_info: dict = None, data_description: dict = None) -> None:
        self.role = role
        self.system_info = SystemInfo(**(system_info or {}))
        self.data_description = DataDescription(**(data_description or {}))

