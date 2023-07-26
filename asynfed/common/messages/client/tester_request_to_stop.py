from asynfed.common.messages import MessageObject
class TesterRequestStop(MessageObject):
    def __init__(self, remote_storage_path, performance, loss):
        self.remote_storage_path = remote_storage_path
        self.performance = performance
        self.loss = loss

