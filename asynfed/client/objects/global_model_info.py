
import numpy as np

from asynfed.common.messages import MessageObject

class GlobalModelInfo(MessageObject):
    def __init__(self, remote_folder_path: str, name: str, version: int, 
                 file_extension: str, total_data_size: int = 0,
                 avg_loss: float = 1000.0, avg_qod: float = 0.00,
                 learning_rate: float = None
                 ):
        self.remote_folder_path = remote_folder_path
        self.name = name
        self.file_extension = file_extension
        self.learning_rate = learning_rate

        self.version = version
        self.avg_loss = avg_loss
        self.avg_qod = avg_qod
        self.total_data_size = total_data_size



    def update(self, version: int, avg_loss: float, avg_qod: float,
               total_data_size: int, learning_rate: float):
        self.new_update = True

        self.version = version
        self.avg_loss = avg_loss
        self.avg_qod = avg_qod
        self.total_data_size = total_data_size
        self.learning_rate = learning_rate


    def get_full_remote_file_path(self):
        return f'{self.remote_folder_path}/{self.version}.{self.file_extension}'
    
    def get_file_name(self):
        return f"{self.version}.{self.file_extension}"
