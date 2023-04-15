import os
from minio import MinioAdmin

from fedasync.commons.conf import StorageConfig
from fedasync.commons.utils.cloud_storage_connector import MinioConnector


class ServerStorage(MinioConnector):
    def __init__(self):
        super().__init__(StorageConfig.ACCESS_KEY, StorageConfig.SECRET_KEY)
        self.admin = MinioAdmin(target='minio')
        # check if bucket global-models is existing or not, if not then create one
        if not self.client.bucket_exists('global-models'):
            self.client.make_bucket('global-models')

    def generate_keys(self, client_id, session_id):
        self.client.make_bucket(client_id)
        new_key = self.admin.user_add(client_id, session_id)

        # Add permissions for the new user
        with open('worker_policy.json', 'w') as f:
            upload_policy = '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": ["s3:PutObject"], ' \
                            '"Resource": ["arn:aws:s3:::%s/*"]},{"Effect": "Allow","Action": [ "s3:GetObject", ' \
                            '"s3:GetBucketLocation"],"Resource": [ "arn:aws:s3:::global-models/*"]}]}' % (
                                client_id)
            f.write(upload_policy)
        self.admin.policy_add(client_id, 'worker_policy.json')
        self.admin.policy_set(client_id, client_id)
        os.remove('worker_policy.json')

        access_key, secret_key = new_key['accessKey'], new_key['secretKey']
        return access_key, secret_key

    def get_newest_global_model(self):
        # get the newest object in the global-models bucket
        objects = self.client.list_objects('global-models', recursive=True, start_after='')
        sorted_objects = sorted(objects, key=lambda obj: obj.last_modified, reverse=True)

        if len(sorted_objects) > 0:
            return sorted_objects[0].object_name
        else:
            print("Bucket is empty.")
            return None

