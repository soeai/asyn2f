import logging

import boto3
from fedasync.commons.conf import StorageConfig
from fedasync.commons.utils.cloud_storage_connector import AWSConnector

LOGGER = logging.getLogger(__name__)


class ServerStorage(AWSConnector):

    def __init__(self):
        super().__init__()
        self.iam = boto3.client('iam', aws_access_key_id=StorageConfig.ACCESS_KEY,
                                aws_secret_access_key=StorageConfig.SECRET_KEY)
        try:
            self.iam.create_user(UserName='client')
            self.iam.attach_user_policy(
                UserName='client',
                PolicyArn='arn:aws:iam::738502987127:policy/FedAsyncClientPolicy'
            )
            client_access_key = self.iam.create_access_key(UserName='client')['AccessKey']
            self.client_access_key_id = client_access_key['AccessKeyId']
            self.client_secret_key = client_access_key['SecretAccessKey']
        except self.iam.exceptions.EntityAlreadyExistsException as e:
            LOGGER.info(e)

    def generate_keys(self, worker_id):
        # Generate an access key and secret key for the user
        self.create_folder(worker_id)
        LOGGER.info(
            f"session: {worker_id} - access key: {self.client_access_key_id} - secret key: {self.client_access_key_id}")
        return self.client_access_key_id, self.client_secret_key

    def create_folder(self, folder_name):
        self._s3.put_object(Bucket='fedasyn', Key=('clients/' + folder_name + '/'))

    def get_newest_global_model(self) -> str:
        # get the newest object in the global-models bucket
        objects = self._s3.list_objects_v2(Bucket='fedasyn', Prefix='global-models/', Delimiter='/')['Contents']
        # Sort the list of objects by LastModified in descending order
        sorted_objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)

        if len(sorted_objects) > 0:
            return sorted_objects[0]['Key']
        else:
            LOGGER.info("Bucket is empty.")
