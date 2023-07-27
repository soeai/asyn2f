import logging
import os


LOGGER = logging.getLogger(__name__)

from asynfed.common.messages.server.server_response_to_init import StorageInfo
from asynfed.common.storage_connectors import MinioConnector
from .boto3 import ServerStorageBoto3


class ServerStorageMinio(MinioConnector, ServerStorageBoto3):
    def __init__(self, storage_info: StorageInfo, parent= None):
        super().__init__(storage_info, parent= parent)
        self._client_access_key: str = None
        self._client_secret_key: str = None

    def set_client_key(self, client_access_key: str, client_secret_key: str):
        self._client_access_key = client_access_key
        self._client_secret_key = client_secret_key

    def get_client_key(self):
        return self._client_access_key, self._client_secret_key

   