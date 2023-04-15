from abc import ABC
from minio import Minio
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class MinioConnector(ABC):

    def __init__(self, access_key, secret_key, region='vn') -> None:
        self.client = Minio('localhost:9000', access_key=access_key, secret_key=secret_key, secure=False, region=region)
        logging.info(f'Connected to Minio server on localhost:9000')

    def upload(self, bucket_name: str, file_path: str):
        """Uploads new global model to MinIO server"""
        filename = file_path.split('/')[-1]

        try:
            self.client.fput_object(bucket_name, filename, file_path)
            # add logging when put successful
            logging.info(f'Successfully uploaded {filename} to {bucket_name}/{filename}')
        except Exception as e:
            logging.error(e)
    
    def download(self, bucket_name, filename: str, save_location='.'):
        """Downloads a file from MinIO server"""

        try:
            self.client.fget_object(bucket_name, filename, save_location + filename)
            logging.info(f'Downloaded {filename}')
        except Exception as e:
            logging.error(e)

