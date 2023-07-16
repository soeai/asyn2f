
from asynfed.commons.messages import MessageObject



class ModelInfo(MessageObject):
    def __init__(self, model_url: str, global_model_name: str, model_version: str):
        self.model_url = model_url
        self.global_model_name = global_model_name
        self.model_version = model_version


class StorageInfo(MessageObject):
    def __init__(self, storage_type: str, access_key: str, secret_key: str, 
                 bucket_name: str, region_name: str, endpoint_url: str = ""):
        self.storage_type = storage_type
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.endpoint_url = endpoint_url


class QueueInfo(MessageObject):
    def __init__(self, training_exchange: str, monitor_queue: str):
        self.training_exchange = training_exchange
        self.monitor_queue = monitor_queue


class ExchangeAt(MessageObject):
    def __init__(self, performance: float = 0.85, epoch: int = 100):
        self.performance = performance
        self.epoch = epoch


class ResponseToInit(MessageObject):
    def __init__(self, session_id: str, model_info: dict, storage_info: dict, queue_info: dict, 
                 exchange_at: dict, reconnect: bool = False):
        self.session_id = session_id
        self.model_info: ModelInfo = ModelInfo(**model_info)
        self.storage_info: StorageInfo = StorageInfo(**storage_info)
        self.queue_info: QueueInfo = QueueInfo(**queue_info)
        self.exchange_at: ExchangeAt = ExchangeAt(**exchange_at) 
        self.reconnect = reconnect

    # def to_dict(self) -> dict:
    #     return {key: value if not isinstance(value, MessageObject) else value.to_dict() for key, value in self.__dict__.items()}