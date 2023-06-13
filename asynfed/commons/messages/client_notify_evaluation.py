from asynfed.commons.messages.message import Message


class ClientNotifyEvaluation(Message):

    def __init__(self,
                 client_id=None,
                 timestamp=None,
                 model_id=None,
                 global_model_version_used=None,
                 loss_value=None,
                 performance=None,
                 ):
        super().__init__()
        self.client_id = client_id
        self.model_id = model_id
        self.timestamp = timestamp
        
        self.global_model_version_used = global_model_version_used
        self.performance = performance
        self.loss_value = loss_value
