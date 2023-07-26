import logging
import boto3
import json


from asynfed.common.utils import AWSConnector
from .boto3_storage_connector import ServerStorageBoto3
from asynfed.common.messages.server.server_response_to_init import StorageInfo

LOGGER = logging.getLogger(__name__)

class ServerStorageAWS(AWSConnector, ServerStorageBoto3):
    def __init__(self, storage_info: StorageInfo, parent= None):
        super().__init__(storage_info, parent= parent)

        self._client_keys = self._create_bucket_access_policy(storage_info= storage_info)
        self._client_access_key_id = self._client_keys['AccessKeyId']
        self._client_secret_key = self._client_keys['SecretAccessKey']


    def get_client_key(self, worker_id):
        # Generate an access key and secret key for the user
        client_folder_full_path = f"clients/{worker_id}/"
        self._s3.put_object(Bucket=self._bucket_name, Key= client_folder_full_path)
        return self._client_access_key_id, self._client_secret_key


    def _create_bucket_access_policy(self, storage_info: StorageInfo) -> dict:

        self.iam = boto3.client('iam', aws_access_key_id= storage_info.access_key,
                                aws_secret_access_key= storage_info.secret_key)

        self._client_name = f'client-{self._bucket_name}'

        try:
            self.iam.create_user(UserName=self._client_name)
        except Exception as e:
            if 'EntityAlreadyExists' in str(e):
                logging.info(f"User {self._client_name} already exists")
            else:
                logging.error(e)

        policy_arn = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "ListBucket",
                    "Effect": "Allow",
                    "Action": [
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{self._bucket_name}",
                        f"arn:aws:s3:::{self._bucket_name}/*"
                    ]
                },
                {
                    "Sid": "GetGlobalModel",
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:GetObjectACL"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{self._bucket_name}/global-models",
                        f"arn:aws:s3:::{self._bucket_name}/global-models/*"
                    ]
                },
                {
                    "Sid": "PutLocalModel",
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:PutObjectACL"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{self._bucket_name}/clients/*"
                    ]
                }
            ]
        }

        try:
            policy = self.iam.create_policy(
                PolicyName=self._bucket_name,
                PolicyDocument=json.dumps(policy_arn),
            )
            self.iam.attach_user_policy(
                UserName=self._client_name,
                PolicyArn=policy['Policy']['Arn'],
            )
        except Exception as e:
            if 'EntityAlreadyExists' in str(e):
                logging.info(f"Policy {self._bucket_name} already exists")
            else:
                logging.error(e)

        self._client_keys = {}
        try:
            self._client_keys: dict = self.iam.create_access_key(UserName=self._client_name)['AccessKey']
        except:
            for key in self.iam.list_access_keys(UserName=self._client_name)['AccessKeyMetadata']:
                if key['UserName'] == self._client_name:
                    self.iam.delete_access_key(
                        UserName=self._client_name,
                        AccessKeyId=key['AccessKeyId']
                    )
            self._client_keys: dict = self.iam.create_access_key(UserName=self._client_name)['AccessKey']

        return self._client_keys
