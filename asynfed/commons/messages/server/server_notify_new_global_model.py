from asynfed.commons.messages import MessageObject
class ServerModelUpdate(MessageObject):
    def __init__(self, chosen_id: list, model_id: str, global_model_name: str, global_model_version: int, 
                        global_model_update_data_size: int, avg_loss: float, avg_qod: float):
        self.chosen_id = chosen_id
        self.model_id = model_id
        self.global_model_version = global_model_version
        self.global_model_name = global_model_name
        self.global_model_update_data_size = global_model_update_data_size
        self.avg_loss = avg_loss
        self.avg_qod = avg_qod

