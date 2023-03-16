from ..messages import Message

class ServerReply(Message):
    # uuid: unique identifer granted for each client from the server when a client joins the network for the first time
    # storage_key: unique key for each client to upload local model to storage service (MinIO)
    def __init__(self, uuid: str, storage_key: str) -> None:
        super().__init__({
            "uuid": uuid,
            "storage_key": storage_key
        })
    
    # # abstract method
    # def to_dict(self) -> Dict:
    #     return {
    #         "uuid": self.uuid,
    #         "storage_key": self.storage_key
    #     }
    
    # abstract method
    def construct_from_dict(self, dict_object: dict):
        self.uuid = dict_object["uuid"]
        self.storage_key = dict_object["storage_key"]