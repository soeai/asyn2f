import os
from abc import ABC
import logging

import boto3
from botocore.client import Config

from time import sleep

logging.getLogger(__name__)


class MinioConnector(ABC):
    """Class for connecting to AWS S3"""
    time_sleep = 10
    def __init__(self, minio_config, parent=None) -> None:
        self.parent_thread = parent
        self.access_key = minio_config['access_key']
        self.secret_key = minio_config['secret_key']
        self.bucket_name = minio_config['bucket_name']
        self.endpoint_url = minio_config['endpoint_url']
        
        self._s3 = boto3.client('s3',
                                endpoint_url=self.endpoint_url,
                                aws_access_key_id=self.access_key, 
                                aws_secret_access_key=self.secret_key, 
                                config=Config(signature_version='s3v4'))
        
        logging.info(f'Connected to MinIO server')


    def upload(self, local_file_path: str, remote_file_path: str, try_time=5):
        """Uploads new global model to AWS"""
        # check if local_file_path is exist, if not create one
        if not os.path.exists(local_file_path):
            os.makedirs(local_file_path.split('/')[:-1])
        # call synchronously
        if self.parent_thread is None:
            try:
                logging.info(f'Uploading {local_file_path} to {remote_file_path}...')
                self._s3.upload_file(local_file_path, self.bucket_name, remote_file_path)
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
                    self._s3.upload_file(local_file_path, self.bucket_name, remote_file_path)
                    logging.info(f'Successfully uploaded {local_file_path} to {remote_file_path}')
                    self.parent_thread.on_upload(True)
                    break
                except Exception as e:
                    logging.error(e)
                    sleep(self.time_sleep)
                    t += 1
            self.parent_thread.on_upload(False)

    def download(self, remote_file_path, local_file_path, try_time=5):
        """Downloads a file from AWS"""
        # call synchronously
        if self.parent_thread is None:
            try:
                logging.info(f'Saving {remote_file_path} to {local_file_path}...')
                self._s3.download_file(self.bucket_name, remote_file_path, local_file_path)
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
                    self._s3.download_file(self.bucket_name, remote_file_path, local_file_path)
                    logging.info(f'Saved {remote_file_path} to {local_file_path}')
                    result = True
                    break
                except Exception as e:
                    logging.error(e)
                    sleep(self.time_sleep)
                    t += 1
                    raise e
            self.parent_thread.on_download(result)
