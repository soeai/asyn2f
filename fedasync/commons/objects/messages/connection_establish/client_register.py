from ..messages import Message


class ClientRegister(Message):
    def __init__(self, dataset_size: int, cpu: str, gpu: str,
                 ram: str) -> None:
        super().__init__({
            "dataset_size": dataset_size,
            "sys_info": {
                "system": "Linux",
                "node": "TTUAI",
                "machine": "x86_64",
                "mac_add": "",
                "cpu": cpu,
                "gpu": gpu,
                "ram": ram,
            },
            "data_desc": {
                "name": "",
                "desc": "use for monitoring later",
                "data_size": 1223
            },
            "qod": {
                "schema": "https://marketplace.com/qod/tab/v1",
                "__comment": "metric here depends on schema"
            }
        })

    def construct_from_dict(self, dict_object: dict):
        self.dataset_size = dict_object["dataset_size"]
        self.cpu = dict_object["cpu"]
        self.gpu = dict_object["gpu"]
        self.ram = dict_object["ram"]
