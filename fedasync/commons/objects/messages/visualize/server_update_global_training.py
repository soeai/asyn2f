from ..messages import Message

# Server update Global Training Info frequently 
# per each period of time (in second or microsecond)
# the reasonable waiting time between each updating period
# the updating period could be dynamic --> also monitoring this attribute
class ServerUpdateGlobalTraining(Message):
    # Add more attributes
    # client_result: dict
        # key: value
        # uuid: [acc, loss]
    def __init__(self, update_version: int, waiting_time: int, global_acc: float, 
                 global_loss: float, client_result: dict) -> None:
        super().__init__({
            "update_version": update_version,
            "waiting_time": waiting_time,
            "global_acc": global_acc,
            "global_loss": global_loss,
            "client_result": client_result
        })
    

    # # abstract method
    # def to_dict(self) -> Dict:
    #     return {
    #         "update_version": self.update_version,
    #         "waiting_time": self.waiting_time,
    #         "global_acc": self.global_acc,
    #         "global_loss": self.global_loss,
    #         "client_result": self.client_result
    #     }  
    
    # abstract method
    def construct_from_dict(self, dict_object: dict):
        self.update_version = dict_object['update_version']
        self.waiting_time = dict_object['waiting_time']
        self.global_acc = dict_object['global_acc']
        self.global_loss = dict_object['global_loss']
        self.client_result = dict_object['client_result']