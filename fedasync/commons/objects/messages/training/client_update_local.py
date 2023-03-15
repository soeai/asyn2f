from ..messages import Message
# from datetime import datetime
 
class ClientUpdateLocal(Message):
    # date_string = "2022-03-15 12:30:00"
    # date_format = "%Y-%m-%d %H:%M:%S"
    # training_time: in second or microsecond
    def __init__(self, uuid: str, latest_global_version: int, 
                 start: str, finish: str, training_time: int, 
                 link: str, acc: float, loss: float, batch_size: int) -> None:
        super().__init__({
            "uuid": uuid,
            "latest_global_version": latest_global_version,
            "start": start,
            "finish": finish,
            "training_time": training_time,
            "link": link,
            "acc": acc,
            "loss": loss,
            "batch_size": batch_size
        })

    # abstract method
    def to_dict(self) -> Dict:
        return {
            "uuid": self.uuid,
            "latest_global_version": self.latest_global_version,
            "start": self.start,
            "finish": self.finish,
            "training_time": self.training_time,
            "link": self.link,
            "acc": self.acc,
            "loss": self.loss,
            "batch_size": self.batch_size
        }
    
    # abstract method
    def construct_from_dict(self, dict_object: dict):
        self.uuid = dict_object["uuid"]
        self.latest_global_version = dict_object["latest_global_version"]
        self.start = dict_object["start"]
        self.finish = dict_object["finish"]
        self.training_time = dict_object["training_time"]
        self.link = dict_object["link"]
        self.acc = dict_object["acc"]
        self.loss = dict_object["loss"]
        self.batch_size = dict_object["batch_size"]