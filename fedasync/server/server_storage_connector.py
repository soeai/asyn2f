import json
import boto3
from fedasync.commons.conf import StorageConfig
from fedasync.commons.utils.cloud_storage_connector import AWSConnector


class ServerStorage(AWSConnector):

    def __init__(self, access_key, secret_key, region_name='ap-southeast-2'):
        super().__init__(access_key, secret_key, region_name)
        self.iam = boto3.client('iam', aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                                region_name=region_name)

    def generate_keys(self, session_id):
        # Create a new user with the session ID as the username
        username = session_id
        self.create_folder(username)
        self.iam.create_user(UserName=username)

        # Define the custom policy that allows read/write access to a specific S3 bucket

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                    ],
                    "Resource": [
                        "arn:aws:s3:::fedasyn/global-models/*",
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                    ],
                    "Resource": [
                        f"arn:aws:s3:::fedasyn/{username}/*",
                    ]
                },
            ]
        }

        # Create the self.s3 policy and get the ARN
        policy_arn = self.s3.create_policy(
            PolicyName=f"{username}-s3-policy",
            PolicyDocument=json.dumps(policy)
        )['Policy']['Arn']

        # Attach the policy to the user
        self.s3.attach_user_policy(
            UserName=username,
            PolicyArn=policy_arn
        )

        # Generate an access key and secret key for the user
        access_key = self.s3.create_access_key(UserName=username)['AccessKey']

        # Print the access key ID and secret access key
        print(f"Access key ID: {access_key['AccessKeyId']}")
        print(f"Secret access key: {access_key['SecretAccessKey']}")
        return access_key['AccessKeyId'], access_key['SecretAccessKey']

    def get_newest_global_model(self):
        # get the newest object in the global-models bucket
        objects = self.s3.list_objects_v2(Bucket='fedasyn-global-models')['Contents']
        # Sort the list of objects by LastModified in descending order
        sorted_objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)

        if len(sorted_objects) > 0:
            return sorted_objects[0]['Key']
        else:
            print("Bucket is empty.")
            return None

    def create_folder(self, folder_name):
        self.s3.put_object(Bucket='fedasyn', Key=(folder_name + '/'))
