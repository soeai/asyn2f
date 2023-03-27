from minio import Minio
from minio import error
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class MinioConnector:
    
    def __init__(self, access_key, secret_key, uuid) -> None:
        self.client = Minio('localhost:9000', access_key=access_key, secret_key=secret_key, secure=False)
        self.uuid = uuid
        logging.info(f'Connected to Minio server')

    def upload(self, filename: str):
        bucket_name = 'asynfl-storage'
        object_name = f'clients/{self.uuid}/{filename}'
        try:
            self.client.fput_object(bucket_name, object_name, filename)
            # add logging when put successful
            logging.info(f'Uploaded {filename} to {bucket_name}/{object_name}')
        except Exception as e:
            logging.error(e)
    
    def download(self, filename: str):
        bucket_name = 'asynfl-storage'
        object_name = f'global-models/{filename}'
        try:
            self.client.fget_object(bucket_name, object_name, filename)
            # add logging when get successful
            logging.info(f'Downloaded {filename} from {bucket_name}/{object_name}')
        except Exception as e:
            logging.error(e)
