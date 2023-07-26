from asynfed.common.messages import MessageObject

class NotifyEvaluation(MessageObject):
    def __init__(self, remote_storage_path: str, performance: float, loss: float):
        self.remote_storage_path = remote_storage_path
        self.performance = performance
        self.loss = loss

