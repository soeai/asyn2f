import logging
import boto3
from asynfed.commons.conf import Config
from asynfed.commons.utils import AWSConnector
LOGGER = logging.getLogger(__name__)
import json
import uuid

class ServerStorage(AWSConnector):

    def __init__(self):
        super().__init__()

        self.iam = boto3.client('iam', aws_access_key_id=Config.STORAGE_ACCESS_KEY,
                                aws_secret_access_key=Config.STORAGE_SECRET_KEY)
        self.client_keys = None

        try:
            logging.info(f"Creating bucket {Config.STORAGE_BUCKET_NAME}")
            self._s3.create_bucket(
                Bucket=Config.STORAGE_BUCKET_NAME,
                CreateBucketConfiguration={'LocationConstraint': Config.STORAGE_REGION_NAME}
            )
            logging.info(f"Created bucket {Config.STORAGE_BUCKET_NAME}")
            self._s3.put_object(Bucket=Config.STORAGE_BUCKET_NAME, Key='global-models/')
        except Exception as e:
            logging.error(e)


        self.client_name = f'client-{Config.STORAGE_BUCKET_NAME}'

        try:
            self.iam.create_user(UserName=self.client_name)
        except Exception as e:
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
                        f"arn:aws:s3:::{Config.STORAGE_BUCKET_NAME}",
                        f"arn:aws:s3:::{Config.STORAGE_BUCKET_NAME}/*"
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
                        f"arn:aws:s3:::{Config.STORAGE_BUCKET_NAME}/global-models",
                        f"arn:aws:s3:::{Config.STORAGE_BUCKET_NAME}/global-models/*"
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
                        f"arn:aws:s3:::{Config.STORAGE_BUCKET_NAME}/clients/*"
                    ]
                }
            ]
        }
        try:
            policy = self.iam.create_policy(
                PolicyName=Config.STORAGE_BUCKET_NAME,
                PolicyDocument=json.dumps(policy_arn),
            )
            self.iam.attach_user_policy(
                UserName=self.client_name,
                PolicyArn=policy['Policy']['Arn'],
            )
        except Exception as e:
            logging.error(e)
            pass # Policy is already exist

        try:
            self.client_keys = self.iam.create_access_key(UserName=self.client_name)['AccessKey']
        except:
            for key in self.iam.list_access_keys(UserName=self.client_name)['AccessKeyMetadata']:
                if key['UserName'] == self.client_name:
                    self.iam.delete_access_key(
                        UserName=self.client_name,
                        AccessKeyId=key['AccessKeyId']
                    )
            self.client_keys = self.iam.create_access_key(UserName=self.client_name)['AccessKey']
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
            LOGGER.info("*" * 20)
            LOGGER.info("NO MODEL EXIST YET")
            LOGGER.info("Uploading initial model...")
            self.upload('./testweight_v1.pkl', 'global-models/testweight_v1.pkl')
            LOGGER.info("Upload initial model succesfully")
            LOGGER.info("*" * 20)
            return 'global-models/testweight_v1.pkl'

    def delete_bucket(self):
        try:
            self._s3.delete_bucket(Bucket=Config.STORAGE_BUCKET_NAME)
            logging.info(f'Success! Bucket {Config.STORAGE_BUCKET_NAME} deleted.')
        except Exception as e:
            logging.error(f'Error! Bucket {Config.STORAGE_BUCKET_NAME} was not deleted. {e}')
