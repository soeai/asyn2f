import boto3
import os
from time import sleep

import sys
print('Python %s on %s' % (sys.version, sys.platform))
sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))



from asynfed.client.client_storage_connector import ClientStorageAWS
from asynfed.commons.utils.aws_storage_connector import AWSConnector
from asynfed.server.server_aws_storage_connector import ServerStorageAWS
from asynfed.commons.conf import Config


Config.STORAGE_ACCESS_KEY= 'AKIA2X4RVJV3VFDERVKZ'
Config.STORAGE_SECRET_KEY = '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'
Config.STORAGE_BUCKET_NAME = 'test-server01234561011010101'
conn = ClientStorageAWS()


remote_file_name = "global-models/testweight_v0.pkl"
local = 'testweight_v0.pkl'
while True:
    conn.download(Config.STORAGE_BUCKET_NAME, remote_file_name, local)
    sleep(5)

