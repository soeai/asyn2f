
from asynfed.commons.messages import MessageObject



class ModelInfo(MessageObject):
    def __init__(self, model_url: str, global_model_name: str, model_version: str):
        self.model_url = model_url
        self.global_model_name = global_model_name
        self.model_version = model_version


class StorageInfo(MessageObject):
    def __init__(self, storage_type: str, access_key: str, secret_key: str, 
                 bucket_name: str, region_name: str, endpoint_url: str = "",
                 client_access_key: str = "", client_secret_key: str = ""):
        self.storage_type = storage_type
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region_name = region_name

        # properties of minio that aws s3 do not have
        # set default value as empty string 
        self.endpoint_url = endpoint_url
        self.client_access_key = client_access_key
        self.client_secret_key = client_secret_key


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

