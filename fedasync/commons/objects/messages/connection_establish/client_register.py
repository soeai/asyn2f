from ..messages import Message

class ClientRegister(Message):
    def __init__(self, dataset_size: int, cpu: str, gpu: str, 
                 ram: str) -> None:
        super().__init__({
            "dataset_size": dataset_size,
            "cpu": cpu,
            "gpu": gpu,
            "ram": ram
        })
    
    # abstract method
    def to_dict(self) -> Dict:
        return {
            "dataset_size": self.dataset_size,
            "cpu": self.cpu,
            "gpu": self.gpu,
            "ram": self.ram
        }
    # abstract method
    def construct_from_dict(self, dict_object: dict):
        self.dataset_size = dict_object["dataset_size"]
        self.cpu = dict_object["cpu"]
        self.gpu = dict_object["gpu"]
        self.ram = dict_object["ram"]