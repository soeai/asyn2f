from fedasync.commons.messages.message import Message


class ServerInitResponseToClient(Message):
    def __init__(self, session_id="", client_id=None, model_url=None, model_version=None, access_key=None, secret_key=None):
        super().__init__()
        self.session_id = session_id
        self.client_id = client_id
        self.model_url = model_url
        self.model_version = model_version
        self.access_key = access_key
        self.secret_key = secret_key
