
class SystemInfo:
    def __init__(self, cpu='intel i5', memory='8GB', gpu='NVIDIA', disk='1TB') -> None:
        """
        Sample
        {
            "cpu": "intel i5",
            "memory": "8GB",
            "gpu": "NVIDIA",
            "disk": "1TB"
        }
        """
        self.cpu = cpu
        self.memory = memory
        self.gpu = gpu
        self.disk = disk


class DataDescription:
    """
    Sample
    {
        "data_type": "image",
        "data_format": "jpg",
        "data_size": "100x100",
        "qod": 0.5
    """
    def __init__(self, data_type='image', data_format='jpg', data_size='100x100', qod=0.5) -> None:
        self.data_type = data_type
        self.data_format = data_format
        self.data_size = data_size
        self.qod = qod


class ClientInitConnection:
    """
    ClientInitConnection class is used to create a message object that can be sent to the server.
    """
    def __init__(self, role="train", system_info=SystemInfo().__dict__, data_description=DataDescription().__dict__) -> None:
        self.role = role
        self.system_info = system_info
        self.data_description = data_description

