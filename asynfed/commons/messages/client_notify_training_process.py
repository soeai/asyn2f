
from asynfed.commons.messages.message import Message

class ClientNotifyTrainingProcess(Message):

    def __init__(self,
                 client_id=None,
                 timestamp=None,
                 global_model_version_used=None,
                 epoch=None,
                 alpha= 1,
                 dataset_size = 1,
                 batch_size=32,
                 current_batch_num=0,
                 train_acc=0,
                 train_loss=0,
                 ):
        super().__init__()
        # client info
        self.timestamp = timestamp
        self.client_id = client_id
        #---- training info ----
        self.global_model_version_used = global_model_version_used
        self.epoch = epoch
        # merging process
        self.alpha = alpha
        self.dataset_size = dataset_size
        # qod is not necessary be sent at each epoch
        # since during the training process
        # the client epoch unchange
        # self.qod = qod 

        self.batch_size = batch_size
        self.current_batch_num = current_batch_num
        self.train_acc = train_acc
        self.train_loss = train_loss
