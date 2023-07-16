
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

    def to_dict(self) -> dict:
        return self.__dict__


class DataDescription:
    """
    Sample
    {
        "data_type": "image",
        "data_format": "jpg",
        "data_size": "100x100",
        "qod": 0.5
    """
    def __init__(self, data_type='image', data_format='jpg', data_size: int = 10, qod: float = 0.5) -> None:
        self.data_type = data_type
        self.data_format = data_format
        self.data_size = data_size
        self.qod = qod

    def to_dict(self) -> dict:
        return self.__dict__


class ClientInitConnection:
    """
    ClientInitConnection class is used to create a message object that can be sent to the server.
    """
    def __init__(self, role: str ="train", system_info: dict = SystemInfo().to_dict(), data_description: dict = DataDescription().to_dict()) -> None:
        self.role = role
        self.system_info: SystemInfo = SystemInfo(**system_info)
        self.data_description: DataDescription = DataDescription(data_description)

    def to_dict(self) -> dict:
        dict_object = {
            "role": self.role,
            "system_info": self.system_info.to_dict(),
            "data_description": self.data_description.to_dict()
        }
        return dict_object

# class ClientInitConnection:
#     """
#     ClientInitConnection class is used to create a message object that can be sent to the server.
#     """
#     def __init__(self, role="train", system_info: dict =SystemInfo().__dict__, data_description: dict =DataDescription().__dict__) -> None:
#         self.role = role
#         self.system_info = system_info
#         self.data_description = data_description

