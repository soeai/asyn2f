from abc import ABC
import logging
import boto3

from fedasync.commons.conf import Config

logging.getLogger(__name__)


class AWSConnector(ABC):
    """Class for connecting to AWS S3"""

    def __init__(self) -> None:

        print(Config.__dict__)
        if "" in [Config.STORAGE_ACCESS_KEY, Config.STORAGE_SECRET_KEY, Config.STORAGE_BUCKET_NAME,
                  Config.STORAGE_REGION_NAME]:
            raise Exception("Storage connector config is not enough, check again.")

        self._s3 = boto3.client('s3', aws_access_key_id=Config.STORAGE_ACCESS_KEY,
                                aws_secret_access_key=Config.STORAGE_SECRET_KEY,
                                region_name=Config.STORAGE_REGION_NAME)
        logging.info(f'Connected to AWS server')

    def upload(self, local_file_path: str, remote_file_path: str, bucket_name: str):
        """Uploads new global model to AWS"""
        try:
            logging.info(f'Uploading {local_file_path} to {remote_file_path}...')
            self._s3.upload_file(local_file_path, bucket_name, remote_file_path)
            logging.info(f'Successfully uploaded {local_file_path} to {remote_file_path}')
            return True
        except Exception as e:
            logging.error(e)
            return False

    def download(self, bucket_name, remote_file_path, local_file_path):
        """Downloads a file from AWS"""
        try:
            logging.info(f'Saving {remote_file_path} to {local_file_path}...')
            self._s3.download_file(bucket_name, remote_file_path, local_file_path)
            logging.info(f'Saved {remote_file_path} to {local_file_path}')
            return True
        except Exception as e:
            logging.error(e)
            return False
