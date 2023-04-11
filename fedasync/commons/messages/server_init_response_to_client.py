from .message import Message


class ServerInitResponseToClient(Message):
    def __init__(self, message: dict = None):
        self.session_id = ""
        self.client_id = ""
        self.model_url = ""
        self.model_version = ""
        self.access_key = ""
        self.secret_key = ""

        # set attribute for this msg object
        self.deserialize(message)





