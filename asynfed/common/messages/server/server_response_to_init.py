
from asynfed.common.messages import MessageObject



class ExchangeAt(MessageObject):
    def __init__(self, performance: float = 0.85, epoch: int = 100):
        self.performance = performance
        self.epoch = epoch



class ModelInfo(MessageObject):
    def __init__(self, url: str, name: str, model_version: str, exchange_at: dict = None):
        self.url = url
        self.name = name
        self.version = model_version
        self.exchange_at = ExchangeAt(**(exchange_at or {}))



# support two type of storage: aws and minio
class StorageInfo(MessageObject):
    def __init__(self, bucket_name: str, region_name: str, minio_endpoint_url: str = None,
                 access_key: str = "", secret_key: str = ""):
        self.minio_endpoint_url = minio_endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region_name = region_name



class ServerReponseToInit(MessageObject):
    def __init__(self, model_info: dict, storage_info: dict, strategy: str = "asynfed"):
        self.strategy = strategy
        self.model_info: ModelInfo = ModelInfo(**model_info)
        self.storage_info: StorageInfo = StorageInfo(**storage_info)
