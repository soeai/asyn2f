import os
from abc import ABC

from minio import Minio
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class MinioConnector(ABC):

    def __init__(self, access_key = None, secret_key=None, uuid=None, region='vn') -> None:
        self.client = Minio('localhost:9000', access_key=access_key, secret_key=secret_key, secure=False, region=region)
        self.uuid = uuid
        logging.info(f'Connected to Minio server on localhost:9000')

    def upload(self, bucket_name: str, filename: str):
        """Uploads new global model to MinIO server"""

        try:
            self.client.fput_object(bucket_name, filename, filename)
            # add logging when put successful
            logging.info(f'Successfully uploaded {filename} to {bucket_name}/{filename}')
        except Exception as e:
            logging.error(e)
    
    def download(self, filename: str):
        """Downloads a file from MinIO server"""

        bucket_name = 'global-models'
        try:
            self.client.fget_object(bucket_name, filename, filename)
            logging.info(f'Downloaded {filename}')
        except Exception as e:
            logging.error(e)

