from asynfed.commons.messages import MessageObject

class ClientModelUpdate(MessageObject):
    def __init__(self, remote_worker_weight_path: str, filename: str, global_version_used: int, loss: float, performance: float):
        self.remote_worker_weight_path = remote_worker_weight_path
        self.filename = filename
        self.global_version_used = global_version_used
        self.loss = loss
        self.performance = performance

