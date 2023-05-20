import logging
import os
import boto3
from asynfed.commons.conf import Config
from asynfed.commons.utils import AWSConnector
LOGGER = logging.getLogger(__name__)


class ServerStorage(AWSConnector):

    def __init__(self, bucket_name: str):
        super().__init__()
        self.bucket_name = bucket_name
        self.iam = boto3.client('iam', aws_access_key_id=Config.STORAGE_ACCESS_KEY,
                                aws_secret_access_key=Config.STORAGE_SECRET_KEY)
        self.client_keys = None

        while True:
            try:
                logging.info(f"Creating bucket {bucket_name}")
                try:
                    self._s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': 'ap-southeast-2'})
                    logging.info(f"Created bucket {bucket_name}")
                    self._s3.put_object(Bucket=Config.STORAGE_BUCKET_NAME, Key=('global-models/'))
                except:
                    pass
                self.iam.create_user(UserName='client')
                # self.iam.attach_user_policy(
                #     UserName='client',
                #     PolicyArn='arn:aws:iam::738502987127:policy/FedAsyncClientPolicy'
                # )
                self.client_keys = self.iam.create_access_key(UserName='client')['AccessKey']
                break

            except self.iam.exceptions.EntityAlreadyExistsException as e:

                try:
                    self.client_keys = self.iam.create_access_key(UserName='client')['AccessKey']
                    break
                except:
                    for key in self.iam.list_access_keys(UserName='client')['AccessKeyMetadata']:
                        if key['UserName'] == "client":
                            self.iam.delete_access_key(
                                UserName='client',
                                AccessKeyId=key['AccessKeyId']
                            )

        self.client_access_key_id = self.client_keys['AccessKeyId']
        self.client_secret_key = self.client_keys['SecretAccessKey']

    def get_client_key(self, worker_id):
        # Generate an access key and secret key for the user
        self.create_folder(worker_id)
        LOGGER.info(
            f"session: {worker_id} - access key: {self.client_access_key_id} - secret key: {self.client_access_key_id}")
        return self.client_access_key_id, self.client_secret_key

    def create_folder(self, folder_name):
        self._s3.put_object(Bucket=Config.STORAGE_BUCKET_NAME, Key=('clients/' + folder_name + '/'))

    def get_newest_global_model(self) -> str:
        # get the newest object in the global-models bucket
        objects = self._s3.list_objects_v2(Bucket=Config.STORAGE_BUCKET_NAME, Prefix='global-models/', Delimiter='/')['Contents']
        # Sort the list of objects by LastModified in descending order
        sorted_objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)

        try:
            if sorted_objects[0]['Key'] == 'global-models/':
                return sorted_objects[1]['Key']
            return sorted_objects[0]['Key']
        except:
            self.upload('../../../testweight_v1.pkl', 'global-models/testweight_v0.pkl', Config.STORAGE_BUCKET_NAME)
            return 'global-models/testweight_v1.pkl'

    def delete_bucket(self):
        try:
            self._s3.delete_bucket(Bucket=self.bucket_name)
            logging.info(f'Success! Bucket {self.bucket_name} deleted.')
        except Exception as e:
            logging.error(f'Error! Bucket {self.bucket_name} was not deleted. {e}')