import json
import boto3
from fedasync.commons.conf import StorageConfig
from fedasync.commons.utils.cloud_storage_connector import AWSConnector


class ServerStorage(AWSConnector):

    def __init__(self, access_key, secret_key):
        super().__init__(access_key, secret_key)
        self.iam = boto3.client('iam', aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        try:
            self.iam.create_user(UserName='client')
            self.iam.attach_user_policy(
                UserName='client',
                PolicyArn='arn:aws:iam::738502987127:policy/FedAsyncClientPolicy'
            )
            access_key = self.iam.create_access_key(UserName='client')['AccessKey']
            self.access_key = access_key['AccessKeyId']
            self.secret_key = access_key['SecretAccessKey']
        except self.iam.exceptions.EntityAlreadyExistsException as e:
            print(e)



    def generate_keys(self, worker_id):
        # Generate an access key and secret key for the user
        self.create_folder(worker_id)
        print(f"session: {worker_id} - access key: {self.access_key} - secret key: {self.access_key}")
        return self.access_key, self.secret_key


    def create_folder(self, folder_name):
        self.s3.put_object(Bucket='fedasyn', Key=('clients/' + folder_name + '/'))

    def get_newest_global_model(self) -> str:
        # get the newest object in the global-models bucket
        objects = self.s3.list_objects_v2(Bucket='fedasyn', Prefix='global-models/', Delimiter='/')['Contents']
        # Sort the list of objects by LastModified in descending order
        sorted_objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)

        if len(sorted_objects) > 0:
            return sorted_objects[0]['Key']
        else:
            print("Bucket is empty.")
