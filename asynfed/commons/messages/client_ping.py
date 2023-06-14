# send ping message to detect where client is alive or not
#
from asynfed.commons.messages.message import Message
from asynfed.commons.utils.time_ultils import time_now


class ClientPing(Message):
    def __init__(self, client_id=None, time=None):
        super().__init__()
        self.client_id = client_id
        self.time = time
