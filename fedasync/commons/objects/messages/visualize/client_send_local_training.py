from ..messages import Message

# Client update info frequently 
# per each batch in each local training epoch
class ClientSendLocalTraining(Message):
    # date_string = "2022-03-15 12:30:00"
    # date_format = "%Y-%m-%d %H:%M:%S"
    # training_time: in second or microsecond

    # Add more attributes
    def __init__(self, uuid: str, start: str, finish: str, training_time: int, 
                 batch_number: int, acc: float, loss: float) -> None:
        super().__init__({
            "uuid": uuid,
            "start": start,
            "finish": finish,
            "training_time": training_time,
            "batch_number": batch_number,
            "acc": acc,
            "loss": loss
        })
    
    # # abstract method
    # def to_dict(self) -> Dict:
    #     return {
    #         'uuid': self.uuid,
    #         'start': self.start,
    #         'finish': self.finish,
    #         'training_time': self.training_time,
    #         'batch_number': self.batch_number,
    #         'acc': self.acc,
    #         'loss': self.loss
    #     }  
    
    
    # abstract method
    def construct_from_dict(self, dict_object: dict):
        self.uuid = dict_object["uuid"]
        self.start = dict_object["start"]
        self.finish = dict_object["finish"]
        self.training_time = dict_object["training_time"]
        self.batch_number = dict_object["batch_number"]
        self.acc = dict_object["acc"]
        self.loss = dict_object["loss"]