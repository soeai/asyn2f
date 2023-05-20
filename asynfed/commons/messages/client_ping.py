# send ping message to detect where client is alive or not
#
from asynfed.commons.messages.message import Message


class ClientPing(Message):
    def __init__(self, client_id=None, timestamp=None):
        super().__init__()
        self.client_id = client_id
        self.timestamp = timestamp
