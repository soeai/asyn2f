import os
import logging
import boto3


logging.getLogger(__name__)

from asynfed.commons.messages.server.server_response_to_init import StorageInfo
from .boto3_storage_connector import Boto3Connector


class AWSConnector(Boto3Connector):
    def __init__(self, storage_info: StorageInfo, parent= None):
        super().__init__(storage_info= storage_info, parent= parent)
        self._time_sleep = 10

    def _setup_connection(self, storage_info: StorageInfo):
        self._access_key = storage_info.access_key
        self._secret_key = storage_info.secret_key
        self._bucket_name = storage_info.bucket_name
        self._region_name = storage_info.region_name


        self._s3 = boto3.client('s3', aws_access_key_id=self._access_key, 
                                aws_secret_access_key=self._secret_key, 
                                region_name=self._region_name)
        try:
            self._s3.list_buckets()
            logging.info(f'Connected to MinIO server')
        except Exception as e:
            logging.error("Invalid AWS Access Key ID or Secret Access Key.")
            raise e
