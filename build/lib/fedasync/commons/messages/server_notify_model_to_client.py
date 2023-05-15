from fedasync.commons.messages.message import Message


class ServerNotifyModelToClient(Message):
    def __init__(self,
                 model_id=None,
                 global_model_version=None,
                 global_model_update_data_size=None,
                 avg_loss=None,
                 chosen_id=None,
                 global_model_name=None):
        super().__init__()
        self.model_id = model_id
        self.global_model_version = global_model_version
        self.global_model_update_data_size = global_model_update_data_size
        self.avg_loss = avg_loss
        self.chosen_id = chosen_id
        self.global_model_name = global_model_name
