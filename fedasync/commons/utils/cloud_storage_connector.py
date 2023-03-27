import os
from minio import Minio
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class MinioConnector:
    
    def __init__(self, access_key, secret_key, uuid, region='vn') -> None:
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

    def upload_folder(self, folder_name: str) -> None:
        """Uploads a folder (i.e: <timestamp>) to MinIO server (used by Worker)"""

        bucket_name = self.uuid
        bucket_prefix = folder_name

        # Check if the folder name is timestamp or not
        try:
            if datetime.fromtimestamp(float(folder_name)):
                # Iterate through all files and subdirectories in the folder
                for root, dirs, files in os.walk(folder_name):
                    for file in files:
                        # Construct the full local path of the file
                        local_path = os.path.join(root, file)

                        # Construct the full object key path
                        object_key = os.path.join(bucket_prefix, os.path.relpath(local_path, folder_name))

                        # Upload the file to MinIO
                        try:
                            self.client.fput_object(bucket_name, object_key, local_path)
                            print(f"Uploaded {local_path} to s3://{bucket_name}/{object_key}")
                        except Exception as e:
                            logging.error(e)
        except ValueError:
            logging.error(f'Folder name {folder_name} is not a timestamp')
