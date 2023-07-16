from asynfed.commons.messages import MessageObject

class PingToClient(MessageObject):
    def __init__(self, client_id):
        self.client_id = client_id


