from asynfed.commons.messages.message import Message

class ClientNotifyModelToServer(Message):

    def __init__(self,
                 client_id=None,
                 timestamp=None,
                 model_id=None,
                 weight_file=None,
                 global_model_version_used=None,
                 loss_value=None,
                 performance=None,
                 ):
        super().__init__()
        # client info
        self.timestamp = timestamp
        self.client_id = client_id
        # download model
        self.model_id = model_id
        self.weight_file = weight_file
        #---- training info ----
        self.global_model_version_used = global_model_version_used
        # performance
        self.loss_value = loss_value
        self.performance = performance

