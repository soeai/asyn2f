from asynfed.common.messages import MessageObject


class GlobalModel(MessageObject):
    # def __init__(self, name: str, version: int, 
    #                     total_data_size: int, avg_loss: float, avg_qod: float):
    def __init__(self, version: int, total_data_size: int = None,
                 avg_loss: float = None, avg_qod: float = None):
        self.version = version
        # self.name = name
        self.total_data_size = total_data_size
        self.avg_qod = avg_qod
        self.avg_loss = avg_loss


class ServerModelUpdate(MessageObject):
    def __init__(self, worker_id: list, global_model: dict, learning_rate: float = None):
        self.worker_id = worker_id
        self.global_model = GlobalModel(**global_model)
        self.learning_rate = learning_rate
