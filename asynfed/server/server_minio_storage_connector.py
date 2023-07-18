import logging
import os


LOGGER = logging.getLogger(__name__)

from asynfed.commons.messages.server.server_response_to_init import StorageInfo
from asynfed.commons.utils import MinioConnector
from .server_boto3_storage_connector import ServerStorageBoto3


class ServerStorageMinio(MinioConnector, ServerStorageBoto3):
    def __init__(self, storage_info: StorageInfo, parent= None):
        super().__init__(storage_info, parent= parent)
        self._client_access_key: str = storage_info.client_access_key
        self._client_secret_key: str = storage_info.client_secret_key


    def get_client_key(self, worker_id):
        # self.create_folder(worker_id)
        client_folder_full_path = f"clients/{worker_id}/"
        self._s3.put_object(Bucket=self._bucket_name, Key= client_folder_full_path)
        return self._client_access_key, self._client_secret_key

   