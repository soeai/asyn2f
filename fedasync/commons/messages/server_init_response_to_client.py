from .message import Message


class ServerInitResponseToClient(Message):
    def __init__(self, message: dict):
        self.session_id = ""
        self.client_id = ""
        self.model_url = ""
        self.access_key = ""

        # set attribute for this msg object
        self.deserialize(message)





