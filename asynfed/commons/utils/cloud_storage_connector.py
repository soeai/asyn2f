from abc import ABC
import logging
import boto3
from time import sleep

logging.getLogger(__name__)


class AWSConnector(ABC):
    """Class for connecting to AWS S3"""
    time_sleep = 10
    def __init__(self, access_key, secret_key, bucket_name, region_name, parent=None) -> None:
        self.parent_thread = parent
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region_name = region_name
        self._s3 = boto3.client('s3', aws_access_key_id=access_key,
                                aws_secret_access_key=secret_key,
                                region_name=region_name)
        logging.info(f'Connected to AWS server')

    def upload(self, local_file_path: str, remote_file_path: str, try_time=5):
        """Uploads new global model to AWS"""
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
                    sleep(AWSConnector.time_sleep)
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
                return True
            except Exception as e:
                print('asdasd')
                raise e
                return False
        else: # call asynchronously
            t = 1
            while t < try_time:
                try:
                    logging.info(f'Saving {remote_file_path} to {local_file_path}...')
                    self._s3.download_file(self.bucket_name, remote_file_path, local_file_path)
                    logging.info(f'Saved {remote_file_path} to {local_file_path}')
                    self.parent_thread.on_download(True)
                    break
                except Exception as e:
                    raise e
                    logging.error(e)
                    sleep(AWSConnector.time_sleep)
                    t += 1
            self.parent_thread.on_download(False)
