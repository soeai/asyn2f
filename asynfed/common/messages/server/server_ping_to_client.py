from asynfed.common.messages import MessageObject

class PingToClient(MessageObject):
    def __init__(self, worker_id: str):
        self.worker_id = worker_id


