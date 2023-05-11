import sys
print('Python %s on %s' % (sys.version, sys.platform))
sys.path.extend(['/home/vtn_ubuntu/ttu/spring23/working_project/AsynFL'])


import boto3
import os

from fedasync.client.client_storage_connector import ClientStorage
from fedasync.commons.utils.cloud_storage_connector import AWSConnector
from fedasync.server.server_storage_connector import ServerStorage


access_key_id = 'AKIA2X4RVJV34CZGNZ67'
secret_access_key = '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'

bucket_name = 'fedasyn'
conn = ServerStorage(access_key_id, secret_access_key)

conn.generate_keys(session_id='test10')
# conn.get_newest_global_model()

# access_key_id = 'AKIA2X4RVJV3ZGTUSFOR'
# secret_access_key = '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'
# conn = ClientStorage(access_key_id, secret_access_key)
# conn.upload('model_weights.npz', 'AKIA2X4RVJV3ZGTUSFOR/model_weights2.npz', 'fedasyn')