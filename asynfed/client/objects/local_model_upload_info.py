
import numpy as np

from asynfed.common.messages import MessageObject

class LocalModelUpdateInfo(MessageObject):
    '''
    this class store all the information needed for both upload the model 
    and the information to notify the server (publish message to queue)
    '''
    def __init__(self, weight_array: np.ndarray = None, local_weight_path: str = None, remote_weight_path: str = None, 
                 filename: str = None, global_version_used: int = None,
                 new_update: bool = False, train_acc: float = 0.0, train_loss: float = 10000.0
                 ):
        self.weight_array = weight_array
        self.local_weight_path = local_weight_path
        self.remote_weight_path = remote_weight_path
        self.filename = filename
        self.global_version_used = global_version_used
        self.new_update = new_update
        self.train_acc = train_acc
        self.train_loss = train_loss


    def update(self, weight_array: np.ndarray, local_weight_path: str, remote_weight_path: str, filename: 
               str, global_version_used: int, train_acc: float, train_loss: float):
        self.new_update = True

        self.weight_array = weight_array
        self.local_weight_path = local_weight_path
        self.remote_weight_path = remote_weight_path
        self.filename = filename
        self.global_version_used = global_version_used
        self.train_acc = train_acc
        self.train_loss = train_loss