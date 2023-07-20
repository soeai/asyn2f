

from asynfed.commons.messages import MessageObject

class LocalModelUpdateInfo(MessageObject):
    def __init__(self, local_weight_path: str = None, remote_weight_path: str = None, filename: str = None):
        self.local_weight_path = local_weight_path
        self.remote_weight_path = remote_weight_path
        self.filename = None 
        self.new_update: bool = False
        self.is_process: bool = False


    def update(self, local_weight_path: str, remote_weight_path: str, filename: str):
        self.new_update = True
        self.local_weight_path = local_weight_path
        self.remote_weight_path = remote_weight_path
        self.filename = filename