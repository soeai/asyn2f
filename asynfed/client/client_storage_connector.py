from asynfed.commons.utils.aws_storage_connector import AWSConnector
from asynfed.commons.utils.minio_storage_connector import MinioConnector


class ClientStorageAWS(AWSConnector):
    def __init__(self, aws_config, parent=None):
        super().__init__(aws_config, parent)


class ClientStorageMinio(MinioConnector):
    def __init__(self, minio_config, parent=None):
        super().__init__(minio_config, parent)