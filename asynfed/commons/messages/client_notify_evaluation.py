from asynfed.commons.messages.message import Message


class ClientNotifyEvaluation(Message):

    def __init__(self,
                 client_id=None,
                 timestamp=None,
                 model_id=None,
                 global_model_version_used=None,
                 loss_value=None,
                 performance=None,
                 alpha=1,
                 batch_size=32,
                 ):
        super().__init__()
        self.client_id = client_id
        self.model_id = model_id
        self.timestamp = timestamp
        
        self.global_model_version_used = global_model_version_used
        self.performance = performance

        self.loss_value = loss_value
        # unused one
        # self.alpha = alpha
        # self.batch_size = batch_size
