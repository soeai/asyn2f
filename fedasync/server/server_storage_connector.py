import os

from minio import MinioAdmin, Minio
import json
from fedasync.commons.utils.cloud_storage_connector import MinioConnector


class ServerStorage(MinioConnector):
    def __init__(self, access_key, secret_key):
        super().__init__(access_key, secret_key)
        self.admin = MinioAdmin(target='minio')

    def generate_key(self, client_id, session_id):
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
