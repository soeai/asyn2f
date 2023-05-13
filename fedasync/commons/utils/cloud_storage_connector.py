from abc import ABC
import logging
import boto3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class AWSConnector(ABC):
    """Class for connecting to AWS S3"""

    def __init__(self, access_key, secret_key) -> None:
        self.s3 = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name='ap-southeast-2')
        logging.info(f'Connected to AWS server')
        self.access_key = access_key
        self.secret_key = secret_key

    def upload(self, local_file_path: str, remote_file_path: str, bucket_name: str):
        """Uploads new global model to AWS"""
        filename = local_file_path.split('/')[-1]

        try:
            logging.info(f'Uploading {local_file_path} to {remote_file_path}...')
            self.s3.upload_file(local_file_path, bucket_name, remote_file_path)
            logging.info(f'Successfully uploaded {local_file_path} to {remote_file_path}')
            return True
        except Exception as e:
            logging.error(e)
            return False

    
    def download(self, bucket_name, remote_file_path, local_file_path):
        """Downloads a file from AWS"""
        try:
            logging.info(f'Saving {remote_file_path} to {local_file_path}...')
            self.s3.download_file(bucket_name, remote_file_path, local_file_path)
            logging.info(f'Saved {remote_file_path} to {local_file_path}')
            return True
        except Exception as e:
            logging.error(e)
            return False


