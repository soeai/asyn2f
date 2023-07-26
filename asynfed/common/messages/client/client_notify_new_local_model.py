from asynfed.common.messages import MessageObject


class ClientModelUpdate(MessageObject):
    def __init__(self, storage_path: str, file_name: str, global_version_used: int, performance: float, loss: float):
        self.storage_path = storage_path
        self.file_name = file_name
        self.global_version_used = global_version_used
        self.performance = performance
        self.loss = loss

