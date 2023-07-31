from asynfed.common.messages import MessageObject
from asynfed.common.messages.server.server_response_to_init import ExchangeAt
from asynfed.common.config import QueueConfig



# class UpdateConditions(MessageObject):
#     def __init__(self, min_workers: int, update_period: int = 40):
#         self.min_workers = min_workers
#         self.update_period = update_period


class CleaningConfig(MessageObject):
    def __init__(self, clean_storage_period: int = 600, global_keep_version_num: int = 10,
                 local_keep_version_num: int = 3):
        self.clean_storage_period = clean_storage_period
        self.global_keep_version_num = global_keep_version_num
        self.local_keep_version_num = local_keep_version_num 


class AWSKey(MessageObject):
    def __init__(self, access_key: str = "", secret_key: str = "", endpoint_url: str= ""):
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint_url = endpoint_url


class MinioKey(AWSKey):
    def __init__(self, access_key: str = "", secret_key: str = "", endpoint_url: str = "",
                 client_access_key: str = "", client_secret_key: str = ""):
        super().__init__(access_key, secret_key, endpoint_url)
        self.client_access_key = client_access_key
        self.client_secret_key = client_secret_key


class CloudStorageConfig(MessageObject):
    def __init__(self, type: str, bucket_name: str, region_name: str,
                    global_model_root_folder: str = "global-models",
                    client_model_root_folder: str = "clients",
                    aws_s3: dict = None, minio: dict = None):
        self.type = type
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.global_model_root_folder = global_model_root_folder
        self.client_model_root_folder = client_model_root_folder

        self.aws_s3 = AWSKey(**aws_s3)
        self.minio = MinioKey(**minio)


class InfluxdbConfig(MessageObject):
    def __init__(self, url: str, token: str, org: str, bucket_name: str):
        self.url = url
        self.token = token
        self.org = org
        self.bucket_name = bucket_name

class Strategy(MessageObject):
    def __init__(self, name: str, m: int, n: int, update_period: int = None):
        self.name = name
        self.m = m
        self.n = n
        self.update_period = update_period


class StopConditions(MessageObject):
    def __init__(self, max_version: int = 300, max_performance: float = 0.95, max_time: int = 180):
        self.max_version = max_version
        self.max_performance = max_performance
        # max time is define in minute
        # need to convert to second
        self.max_time = max_time * 60


class ModelConfig(MessageObject):
    def __init__(self, name: str = "", initial_model_path: str = "initial_model.pkl", 
                 file_extension: str = "pkl", stop_conditions: dict = None,
                 model_exchange_at: dict = None):
        self.name = name
        self.initial_model_path = initial_model_path
        self.file_extension = file_extension

        # these 2 objects support default values

        stop_conditions = stop_conditions or {}
        model_exchange_at = model_exchange_at or {}
        self.model_exchange_at = ExchangeAt(**model_exchange_at)
        self.stop_conditions = StopConditions(**stop_conditions)


class ServerConfig(MessageObject):
    def __init__(self, server_id: str, ping_period: int = 300, save_log: bool = True, 
                 model_config: dict = None, cleaning_config: dict = None, 
                 cloud_storage: dict = None, queue_consumer: dict = None,
                 queue_producer: dict = None, influxdb: dict = None, strategy: dict = None
                 ):

        # these property provide default values
        self.ping_period = ping_period
        self.save_log = save_log

        # this object provide default values
        cleaning_config = cleaning_config or {}

        # these properties need to correctly specify
        self.server_id = server_id

        self.model_config = ModelConfig(**model_config)
        self.strategy = Strategy(**strategy)
        self.cleaning_config = CleaningConfig(**cleaning_config)
        
        # self.update_conditions = UpdateConditions(**update_conditions)
        self.cloud_storage = CloudStorageConfig(**cloud_storage)
        self.queue_consumer = QueueConfig(**queue_consumer)
        self.queue_producer = QueueConfig(**queue_producer)
        self.influxdb = InfluxdbConfig(**influxdb)
