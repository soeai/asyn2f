import os
from abc import ABC
import logging
import minio
from time import sleep

logging.getLogger(__name__)


class MinioConnector(ABC):
    """Class for connecting to AWS S3"""
    time_sleep = 10
    def __init__(self, minio_config, parent=None) -> None:
        self.parent_thread = parent
        self.endpoint = minio_config['endpoint']
        self.access_key = minio_config['access_key']
        self.secret_key = minio_config['secret_key']
        self.bucket_name = minio_config['bucket_name']
        self.region_name = minio_config['region_name']
        self._minio_client = minio.Minio(self.endpoint,access_key=self.access_key,secret_key=self.secret_key)
        # self._s3 = boto3.Session().client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region_name)
        logging.info(f'Connected to Minio server')

    def upload(self, local_file_path: str, remote_file_path: str, try_time=5):
        """Uploads new global model to AWS"""
        # check if local_file_path is exist, if not create one
        if not os.path.exists(local_file_path):
            os.makedirs(local_file_path.split('/')[:-1])
        # call synchronously
        if self.parent_thread is None:
            try:
                logging.info(f'Uploading {local_file_path} to {remote_file_path}...')
                self._minio_client.fput_object(self.bucket_name, remote_file_path, local_file_path)
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
                    self._minio_client.fput_object(self.bucket_name, remote_file_path, local_file_path)
                    logging.info(f'Successfully uploaded {local_file_path} to {remote_file_path}')
                    self.parent_thread.on_upload(True)
                    break
                except Exception as e:
                    logging.error(e)
                    sleep(MinioConnector.time_sleep)
                    t += 1
            self.parent_thread.on_upload(False)

    def download(self, remote_file_path, local_file_path, try_time=5):
        """Downloads a file from AWS"""
        # call synchronously
        if self.parent_thread is None:
            try:
                logging.info(f'Saving {remote_file_path} to {local_file_path}...')
                self._minio_client.fget_object(self.bucket_name, remote_file_path, local_file_path)
                logging.info(f'Saved {remote_file_path} to {local_file_path}')
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
                    self._minio_client.fget_object(self.bucket_name, remote_file_path, local_file_path)
                    logging.info(f'Saved {remote_file_path} to {local_file_path}')
                    result = True
                    break
                except Exception as e:
                    raise e
                    logging.error(e)
                    sleep(MinioConnector.time_sleep)
                    t += 1
            self.parent_thread.on_download(result)
