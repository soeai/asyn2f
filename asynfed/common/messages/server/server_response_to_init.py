
from asynfed.common.messages import MessageObject



class ExchangeAt(MessageObject):
    def __init__(self, performance: float = 0.85, epoch: int = 100):
        self.performance = performance
        self.epoch = epoch



class ModelInfo(MessageObject):
    def __init__(self, global_folder: str, name: str, version: str, file_extension: str, 
                 learning_rate: float = None, exchange_at: dict = None):
        # url = "{global_folder}/{name}/{version}.{file_extension}"
        self.global_folder = global_folder
        self.name = name
        self.version = version
        self.file_extension = file_extension
        self.exchange_at = ExchangeAt(**(exchange_at or {}))
        self.learning_rate = learning_rate



# support two type of storage: aws and minio
class StorageInfo(MessageObject):
    def __init__(self, bucket_name: str, region_name: str, client_upload_folder: str = "", 
                        type: str = "minio", endpoint_url: str = None,
                        access_key: str = "", secret_key: str = "", *args, **kwargs):
        self.type = type
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.client_upload_folder = client_upload_folder


class ServerRespondToInit(MessageObject):
    def __init__(self, model_info: dict, epoch_update_frequency: int,
                 storage_info: dict, strategy: str = "asynfed"):
        self.strategy = strategy
        self.epoch_update_frequency = epoch_update_frequency
        self.model_info: ModelInfo = ModelInfo(**model_info)
        self.storage_info: StorageInfo = StorageInfo(**storage_info)
