import boto3
import os
from dotenv import load_dotenv
from time import sleep

import sys
print('Python %s on %s' % (sys.version, sys.platform))
sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))



from asynfed.client.client_storage_connector import ClientStorage
from asynfed.commons.utils.cloud_storage_connector import AWSConnector
from asynfed.server.server_storage_connector import ServerStorage
from asynfed.commons.conf import Config

# access_key_id = os.getenv('acces_key')
# secret_access_key = os.getenv('secret_key')
# bucket_name = 'fedasyn'
# conn = ServerStorage(access_key_id, secret_access_key)
# conn.generate_keys(session_id='test101')
# print(conn.get_newest_global_model())

Config.STORAGE_ACCESS_KEY= 'AKIA2X4RVJV3VFDERVKZ'
Config.STORAGE_SECRET_KEY = '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'
Config.STORAGE_BUCKET_NAME = 'test-server01234561011010101'
conn = ClientStorage()
# conn.upload('./model_weights.pkl', f'{access_key_id}/model_weights.pkl', 'fedasyn')

remote_file_name = "global-models/testweight_v0.pkl"
local = 'testweight_v0.pkl'
while True:
    conn.download(Config.STORAGE_BUCKET_NAME, remote_file_name, local)
    sleep(5)

