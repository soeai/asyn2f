from asynfed.common.messages import MessageObject

class PingToClient(MessageObject):
    def __init__(self, client_id: str):
        self.client_id = client_id


