from asynfed.commons.messages.message import Message


class ClientNotifyModelToServer(Message):

    def __init__(self,
                 client_id=None,
                 model_id=None,
                 global_model_version_used=None,
                 timestamp=None,
                 loss_value=None,
                 weight_file=None,
                 performance=None,
                 batch_size=32,
                 alpha=1):
        super().__init__()
        self.client_id = client_id
        self.model_id = model_id
        self.global_model_version_used = global_model_version_used
        self.timestamp = timestamp
        self.loss_value = loss_value
        self.weight_file = weight_file
        self.performance = performance
        self.batch_size = batch_size
        self.alpha = alpha
