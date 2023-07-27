import logging
import sys
import re
from abc import abstractmethod

import os

from typing import List
from time import sleep 

LOGGER = logging.getLogger(__name__)

from asynfed.common.messages.server.server_response_to_init import StorageInfo
from asynfed.common.storage_connectors import Boto3Connector

class ServerStorageBoto3(Boto3Connector):
    def __init__(self, storage_info: StorageInfo, parent= None):
        super().__init__(storage_info, parent= parent)
        self._create_bucket()


    @abstractmethod
    def get_client_key(self):
        pass

    # @abstractmethod
    def _create_bucket(self):
        # check whether the bucket name is in the valid format
        valid_bucket_name = self._check_valid_bucket_name()
        if valid_bucket_name:
            try:
                logging.info(f"Creating bucket {self._bucket_name}")
                self._s3.create_bucket(
                    Bucket=self._bucket_name,
                )            
                logging.info(f"Created bucket {self._bucket_name}")
                # self._s3.put_object(Bucket=self._bucket_name, Key= f'{self._global_model_root_folder}/')

            except Exception as e:
                if 'BucketAlreadyOwnedByYou' in str(e):
                    logging.info(f"Bucket {self._bucket_name} already exists")
                else:
                    logging.info("=" * 20)
                    logging.error(e)
                    logging.info("=" * 20)
                    sys.exit(0)
                    
        else:
            logging.info(f"Bucket name {self._bucket_name} is not valid. Exit the program")
            sys.exit(0)


 
    def get_newest_global_model(self) -> str:
        # get the newest object in the global folders inside the bucket
        # print(self._global_model_root_folder)
        folder =  f"{self._global_model_root_folder}/"
        objects = self._s3.list_objects_v2(Bucket=self._bucket_name, Prefix= folder, Delimiter='/')['Contents']
        # Exclude the prefix itself
        objects = [obj for obj in objects if obj['Key'] != folder]

        # print(objects)

        # Sort the list of objects by LastModified in descending order
        sorted_objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)
        
        try:
            if sorted_objects[0]['Key'] == folder:
                LOGGER.info(sorted_objects)
                return sorted_objects[1]['Key']
            return sorted_objects[0]['Key']
        
        except:
            LOGGER.info("*" * 20)
            LOGGER.info("NO MODEL EXIST YET")
            LOGGER.info("Uploading initial model...")
            current_folder = os.getcwd()

            local_weight_path = os.path.join(current_folder, self._initial_model_path)
            remote_weight_path = os.path.join(self._global_model_root_folder, f"1.{self._file_extension}")

            self.upload(local_file_path= local_weight_path, remote_file_path= remote_weight_path)
            LOGGER.info(f"Upload initial model {remote_weight_path} succesfully")
            LOGGER.info("*" * 20)
            return remote_weight_path


    def load_model_config(self, global_model_root_folder: str, initial_model_path: str, 
                          file_extension: str):
        self._global_model_root_folder = global_model_root_folder
        self._s3.put_object(Bucket=self._bucket_name, Key= f'{global_model_root_folder}/')

        self._initial_model_path = initial_model_path
        self._file_extension = file_extension


    def list_files(self, folder_path):
        """Lists all files in the specified client_id folder within the MinIO bucket"""
        try:
            response = self._s3.list_objects_v2(Bucket=self._bucket_name, Prefix=folder_path, Delimiter='/')
            files = []

            if 'Contents' in response:
                files += [file['Key'].replace(folder_path, '') for file in response['Contents']]

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


    # def delete_bucket(self):
    #     try:
    #         self._s3.delete_bucket(Bucket=self._bucket_name)
    #         logging.info(f'Success! Bucket {self._bucket_name} deleted.')
    #     except Exception as e:
    #         logging.error(f'Error! Bucket {self._bucket_name} was not deleted. {e}')
