from abc import ABC, abstractmethod
import os
import logging
from time import sleep

logging.getLogger(__name__)

from asynfed.common.messages.server.server_response_to_init import StorageInfo


class Boto3Connector(ABC):
    time_sleep = 10
    def __init__(self, storage_info: StorageInfo, parent= None):
        self._parent_thread = parent
        self._bucket_name: str = ""
        self._time_sleep: int = 0

        # s3 is the return object of the function boto3.client 
        self._s3 = None
        self._setup_connection(storage_info= storage_info)


    @abstractmethod
    def _setup_connection(self, storage_info: StorageInfo):
        pass

    def upload(self, local_file_path: str, remote_file_path: str, try_time=5):
        # check if local_file_path is exist, if not create one
        print(local_file_path)
        if not os.path.exists(local_file_path):
            print(f'File {local_file_path} does not exist, creating one...')
            os.makedirs(local_file_path.split(os.path.sep)[:-1])
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
                    sleep(self._time_sleep)
                    t += 1
            self._parent_thread.on_upload(False)


    def download(self, remote_file_path, local_file_path, try_time= 5):
        
        # call synchronously
        if self._parent_thread is None:
            try:
                logging.info(f'Saving {remote_file_path} to {local_file_path}...')
                self._s3.download_file(self._bucket_name, remote_file_path, local_file_path)
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
                    self._s3.download_file(self._bucket_name, remote_file_path, local_file_path)
                    logging.info(f'Saved {remote_file_path} to {local_file_path}')
                    result = True
                    break
                except Exception as e:
                    logging.error(e)
                    sleep(self._time_sleep)
                    t += 1
                    raise e
            self._parent_thread.on_download(result)

    def is_file_exists(self, file_path: str) -> bool:
        """
        Check if a file with the given file_path exists in the bucket with the given bucket_name.
        
        Args:
            bucket_name (str): The name of the S3 bucket.
            file_path (str): The path of the file to check.

        Returns:
            bool: True if the file exists in the bucket, False otherwise.
        """
        try:
            response = self._s3.list_objects_v2(Bucket=self._bucket_name, Prefix=file_path)
            for obj in response.get('Contents', []):
                if obj['Key'] == file_path:
                    return True
            return False
        except Exception as e:
            logging.error(f"Error occurred while checking if file {file_path} exists in bucket {self._bucket_name}. Error: {e}")
            return False
