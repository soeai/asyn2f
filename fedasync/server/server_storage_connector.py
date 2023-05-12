import json
import boto3
from fedasync.commons.conf import StorageConfig
from fedasync.commons.utils.cloud_storage_connector import AWSConnector


class ServerStorage(AWSConnector):

    def __init__(self, access_key, secret_key):
        super().__init__(access_key, secret_key)
        self.iam = boto3.client('iam', aws_access_key_id=access_key, aws_secret_access_key=secret_key)

    def generate_keys(self, session_id):
        # Generate an access key and secret key for the user
        self.iam.create_user(UserName=session_id)
        access_key = self.iam.create_access_key(UserName=session_id)['AccessKey']
        self.access_key = access_key['AccessKeyId']

        # Create a new user
        self.create_folder(self.access_key)


        # Define the custom policy that allows read/write access to a specific S3 bucket

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:ListBucket",
                    ],
                    "Resource": [
                        "arn:aws:s3:::fedasyn",
                        "arn:aws:s3:::fedasyn/*",
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:GetObjectACL",
                    ],
                    "Resource": [
                        "arn:aws:s3:::fedasyn/global-models",
                        "arn:aws:s3:::fedasyn/global-models/*",
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:PutObjectACL",
                    ],
                    "Resource": [
                        f"arn:aws:s3:::fedasyn/{self.access_key}/*",
                    ]
                },
            ]
        }

        # Create the self.s3 policy and get the ARN
        policy_arn = self.iam.create_policy(
            PolicyName=f"{self.access_key}-s3-policy",
            PolicyDocument=json.dumps(policy)
        )['Policy']['Arn']

        # Attach the policy to the user
        self.iam.attach_user_policy(
            UserName=session_id,
            PolicyArn=policy_arn
        )

        # Print the access key ID and secret access key
        print(f"session: {session_id} - access key: {access_key['AccessKeyId']} - secret key: {access_key['SecretAccessKey']}")
        return access_key['AccessKeyId'], access_key['SecretAccessKey']


    def create_folder(self, folder_name):
        self.s3.put_object(Bucket='fedasyn', Key=(folder_name + '/'))

    def get_newest_global_model(self) -> str:
        # get the newest object in the global-models bucket
        objects = self.s3.list_objects_v2(Bucket='fedasyn', Prefix='global-models/', Delimiter='/')['Contents']
        # Sort the list of objects by LastModified in descending order
        sorted_objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)

        if len(sorted_objects) > 0:
            return sorted_objects[0]['Key']
        else:
            print("Bucket is empty.")
