from ..messages import Message

class ClientSendRunningStatus(Message):
    def __init__(self, uuid: str) -> None:
        super().__init__({
            "uuid": uuid
        })
    
    # abstract method
    # def to_dict(self) -> Dict:
    #     return {
    #         "uuid": self.uuid
    #     }
    
    # abstract method
    def construct_from_dict(self, dict_object: dict):
        self.uuid = dict_object["uuid"]