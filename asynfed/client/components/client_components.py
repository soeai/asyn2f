from .cloud_storage_connectors import CloudStorageAWS, CloudStorageMinio
from .queue_connectors import AmqpConsumer, AmqpProducer
from .storage_cleaner import StorageCleaner



# from asynfed.client import Client
from asynfed.client.config_structure import QueueConfig

from asynfed.common.messages.server.server_response_to_init import StorageInfo


class ClientComponents():
    def __init__(self, host_object, queue_producer_conf: QueueConfig, 
                 queue_consumer_conf: QueueConfig, storage_cleaner_conf: dict):
        self.queue_consumer = AmqpConsumer(config= queue_consumer_conf, host_object= host_object)
        self.queue_producer = AmqpProducer(queue_producer_conf)
        self.storage_cleaner = StorageCleaner(**storage_cleaner_conf)

        self.cloud_storage = None



    def add_cloud_storage(self, storage_info: StorageInfo = None):
        if storage_info.type == "aws_s3":
            self.cloud_storage = CloudStorageAWS(storage_info)
        else:
            self.cloud_storage = CloudStorageMinio(storage_info)