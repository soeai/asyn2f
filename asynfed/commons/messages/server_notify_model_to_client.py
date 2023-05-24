from asynfed.commons.messages.message import Message


class ServerNotifyModelToClient(Message):
    def __init__(self,
                 chosen_id=None,
                 model_id=None,
                 global_model_name=None,
                 global_model_version=None,
                 global_model_update_data_size= 0,
                 avg_loss=1,
                 avg_qod = 0.5,
                 ):
        super().__init__()
        # list of chosen client to start training
        self.chosen_id = chosen_id
        # download info
        self.model_id = model_id
        self.global_model_version = global_model_version
        self.global_model_name = global_model_name
        # training info
        self.global_model_update_data_size = global_model_update_data_size
        # not define yet
        self.avg_loss = avg_loss
        self.avg_qod = avg_qod

