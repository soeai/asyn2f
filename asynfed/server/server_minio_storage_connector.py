import logging
import sys
import re

from typing import List
from asynfed.commons.utils import MinioConnector
from time import sleep 

LOGGER = logging.getLogger(__name__)

from asynfed.commons.messages.server.server_response_to_init import StorageInfo

class ServerStorageMinio(MinioConnector):
    def __init__(self, storage_info: StorageInfo):
        super().__init__(storage_info)
        self.create_bucket()
        self._client_access_key: str = storage_info.client_access_key
        self._client_secret_key: str = storage_info.client_secret_key

    def create_bucket(self):
        # check whether the bucket name is in the valid format
        valid_bucket_name = self._check_valid_bucket_name()
        if valid_bucket_name:
            try:
                logging.info(f"Creating bucket {self._bucket_name}")
                self._s3.create_bucket(
                    Bucket=self._bucket_name,
                )            
                logging.info(f"Created bucket {self._bucket_name}")
                self._s3.put_object(Bucket=self._bucket_name, Key='global-models/')

            except Exception as e:
                if 'BucketAlreadyOwnedByYou' in str(e):
                    logging.info(f"Bucket {self._bucket_name} already exists")
                else:
                    logging.info("=" * 20)
                    logging.error(e)
                    logging.info("=" * 20)
                    sys.exit(0)
        else:
            sys.exit(0)


    def get_client_key(self, worker_id):
        self.create_folder(worker_id)
        return self._client_access_key, self._client_secret_key

    def create_folder(self, folder_name):
        self._s3.put_object(Bucket=self._bucket_name, Key=('clients/' + folder_name + '/'))

    def get_newest_global_model(self) -> str:
        # get the newest object in the global-models bucket
        objects = self._s3.list_objects_v2(Bucket=self._bucket_name, Prefix='global-models/', Delimiter='/')['Contents']
        # Sort the list of objects by LastModified in descending order
        sorted_objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)

        try:
            if sorted_objects[0]['Key'] == 'global-models/':
                LOGGER.info(sorted_objects)
                return sorted_objects[1]['Key']
            return sorted_objects[0]['Key']
        except:
            LOGGER.info("*" * 20)
            LOGGER.info("NO MODEL EXIST YET")
            LOGGER.info("Uploading initial model...")
            self.upload('./testweight_v1.pkl', 'global-models/testweight_v1.pkl')
            LOGGER.info("Upload initial model succesfully")
            LOGGER.info("*" * 20)
            return 'global-models/testweight_v1.pkl'

    # def delete_bucket(self):
    #     try:
    #         self._s3.delete_bucket(Bucket=self._bucket_name)
    #         logging.info(f'Success! Bucket {self._bucket_name} deleted.')
    #     except Exception as e:
    #         logging.error(f'Error! Bucket {self._bucket_name} was not deleted. {e}')


    def list_files(self, parent_folder: str = "clients", target_folder: str = ''):
        """Lists all files in the specified folder and its subfolders within the MinIO bucket"""
        try:
            response = self._s3.list_objects_v2(Bucket=self._bucket_name, Prefix=parent_folder, Delimiter='/')
            files = []

            if 'Contents' in response:
                files += [file['Key'] for file in response['Contents'] if target_folder in file['Key']]

            if 'CommonPrefixes' in response:
                subfolders = [prefix['Prefix'] for prefix in response['CommonPrefixes']]
                for subfolder in subfolders:
                    files += self.list_files(subfolder, target_folder=target_folder)


            # remove the target folder path
            files = [file for file in files if len(file.split("/")[-1]) != 0]
            return files
        except Exception as e:
            logging.error(e)
            return []

        
    def delete_files(self, file_keys: List[str]):
        """Deletes a list of files from the MinIO bucket"""
        try:
            objects = [{'Key': file_key} for file_key in file_keys]
            delete_request = {'Objects': objects}

            self._s3.delete_objects(Bucket=self._bucket_name, Delete=delete_request)
            return True

        except Exception as e:
            logging.error(e)
            return False


    def _check_valid_bucket_name(self) -> bool:
        # Bucket name length should be between 3 and 63
        if len(self._bucket_name) < 3 or len(self._bucket_name) > 63:
            logging.info("Bucket name length should be between 3 and 63 characters.")
            return False

        # Bucket name should start and end with a number or lowercase letter
        if not re.match('^[a-z0-9]', self._bucket_name) or not re.match('.*[a-z0-9]$', self._bucket_name):
            logging.info("Bucket name should start and end with a lowercase letter or number.")
            return False

        # Bucket name should not contain underscore, double dots, dash next to dots, 
        # end with a dash, start with 'xn--', end with '-s3alias' or '--ol-s3'.
        if re.search('_|\.\.|\-$|\-\.|\.\-|^xn--|\-s3alias$|--ol-s3$', self._bucket_name):
            logging.info("Bucket name should not contain underscore, double dots, dash next to dots, end with a dash, start with 'xn--', end with '-s3alias' or '--ol-s3'.")
            return False

        # Bucket name should not be in IP format
        if re.match('\d+\.\d+\.\d+\.\d+', self._bucket_name):
            logging.info("Bucket name should not be in IP format.")
            return False

        return True