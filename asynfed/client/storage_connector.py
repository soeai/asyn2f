from asynfed.common.storage_connectors import AWSConnector
from asynfed.common.storage_connectors import MinioConnector

from asynfed.common.messages.server.server_response_to_init import StorageInfo


class ClientStorageAWS(AWSConnector):
    def __init__(self, config: StorageInfo, parent=None):
        # server pass client keys as in these variables

        super().__init__(config, parent)


class ClientStorageMinio(MinioConnector):
    def __init__(self, config: StorageInfo, parent=None):
        # server pass client keys as in these variables
        # config.access_key = config.client_access_key
        # config.secret_key = config.client_secret_key
        super().__init__(config, parent)