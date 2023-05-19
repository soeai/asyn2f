from asynfed.commons.messages.message import Message


class ErrorMessage(Message):
    def __init__(self, error_message, client_id):
        self.error_message = error_message
        self.client_id = client_id
