from typing import Any, Union, Dict

from .message import Message


class ServerNotifyModelToClient(Message):
    def __init__(self, message: Union[str, Dict] = None):
        self.model_id = ""
        self.global_model_version = ""
        self.global_model_update_data_size = 3424
        self.avg_loss = 0.2
        self.chosen_id = []
        self.global_model_name = ""

        self.deserialize(message)
