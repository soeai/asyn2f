import boto3
import os
from dotenv import load_dotenv

import sys
print('Python %s on %s' % (sys.version, sys.platform))
sys.path.extend(['/home/vtn_ubuntu/ttu/spring23/working_project/AsynFL'])



from fedasync.client.client_storage_connector import ClientStorage
from fedasync.commons.utils.cloud_storage_connector import AWSConnector
from fedasync.server.server_storage_connector import ServerStorage

# access_key_id = os.getenv('acces_key')
# secret_access_key = os.getenv('secret_key')
# bucket_name = 'fedasyn'
# conn = ServerStorage(access_key_id, secret_access_key)
# conn.generate_keys(session_id='test101')
# print(conn.get_newest_global_model())

access_key_id = os.getenv('client_access_key')
secret_access_key = os.getenv('client_secret_key')
conn = ClientStorage(access_key_id, secret_access_key)
# conn.upload('./model_weights.pkl', f'{access_key_id}/model_weights.pkl', 'fedasyn')

remote_file_name = "global-models/99126837-5f30-44b8-9375-3564500249d7_v1.pkl"
local = './data/client/global_weights/99126837-5f30-44b8-9375-3564500249d7_v1.pkl'
conn.download('fedasyn', remote_file_name, local)

