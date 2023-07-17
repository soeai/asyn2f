import os
from abc import ABC
import logging

import boto3
from botocore.client import Config

from time import sleep

logging.getLogger(__name__)

from asynfed.commons.messages.server.server_response_to_init import StorageInfo

class MinioConnector(ABC):
    """Class for connecting to AWS S3"""
    time_sleep = 10
    def __init__(self, storage_info: StorageInfo, parent=None) -> None:
        self._parent_thread = parent
        self._access_key = storage_info.access_key
        self._secret_key = storage_info.secret_key
        self._bucket_name = storage_info.bucket_name
        self._endpoint_url = storage_info.endpoint_url

        self._s3 = boto3.client('s3',
                                endpoint_url=self._endpoint_url,
                                aws_access_key_id=self._access_key, 
                                aws_secret_access_key=self._secret_key, 
                                config=Config(signature_version='s3v4'))

        try:
            self._s3.list_buckets()
            logging.info(f'Connected to MinIO server')
        except Exception as e:
            logging.error("Invalid AWS Access Key ID or Secret Access Key.")
            raise e


    def upload(self, local_file_path: str, remote_file_path: str, try_time=5):
        """Uploads new global model to AWS"""
        # check if local_file_path is exist, if not create one
        if not os.path.exists(local_file_path):
            os.makedirs(local_file_path.split('/')[:-1])
        # call synchronously
        if self._parent_thread is None:
            try:
                logging.info(f'Uploading {local_file_path} to {remote_file_path}...')
                self._s3.upload_file(local_file_path, self._bucket_name, remote_file_path)
                logging.info(f'Successfully uploaded {local_file_path} to {remote_file_path}')
                return True
            except Exception as e:
                logging.error(e)
                return False
        else: # call asynchronously
            t = 1
            while t < try_time:
                try:
                    logging.info(f'Uploading {local_file_path} to {remote_file_path}...')
                    self._s3.upload_file(local_file_path, self._bucket_name, remote_file_path)
                    logging.info(f'Successfully uploaded {local_file_path} to {remote_file_path}')
                    self._parent_thread.on_upload(True)
                    break
                except Exception as e:
                    logging.error(e)
                    sleep(self.time_sleep)
                    t += 1
            self._parent_thread.on_upload(False)

    def download(self, remote_file_path, local_file_path, try_time=5):
        """Downloads a file from AWS"""
        # call synchronously
        if self._parent_thread is None:
            try:
                logging.info(f'Saving {remote_file_path} to {local_file_path}...')
                self._s3.download_file(self._bucket_name, remote_file_path, local_file_path)
                logging.info(f'Saved {remote_file_path} to {local_file_path}')
                downloaded = True
                return True
            except Exception as e:
                # raise e
                return False
        else: # call asynchronously
            result = False
            t = 1
            while t < try_time:
                try:
                    logging.info(f'Saving {remote_file_path} to {local_file_path}...')
                    self._s3.download_file(self._bucket_name, remote_file_path, local_file_path)
                    logging.info(f'Saved {remote_file_path} to {local_file_path}')
                    result = True
                    break
                except Exception as e:
                    logging.error(e)
                    sleep(self.time_sleep)
                    t += 1
                    raise e
            self._parent_thread.on_download(result)
