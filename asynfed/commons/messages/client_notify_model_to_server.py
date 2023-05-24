from asynfed.commons.messages.message import Message

class ClientNotifyModelToServer(Message):

    def __init__(self,
                 client_id=None,
                 timestamp=None,
                 model_id=None,
                 weight_file=None,
                 global_model_version_used=None,
                 loss_value=None,
                 performance=None,
                 alpha= 1,
                 qod = 1,
                 dataset_size = 1,
                 batch_size=32,
                 ):
        super().__init__()
        # client info
        self.timestamp = timestamp
        self.client_id = client_id
        # download model
        self.model_id = model_id
        self.weight_file = weight_file
        #---- training info ----
        self.global_model_version_used = global_model_version_used
        # performance
        self.loss_value = loss_value
        self.performance = performance
        # merging process
        self.alpha = alpha
        self.dataset_size = dataset_size
        # qod is not necessary be sent at each epoch
        # since during the training process
        # the client epoch unchange
        # self.qod = qod 

        # unused one
        self.batch_size = batch_size
