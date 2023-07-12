import os, sys
# asynfed/server/test_server_minio.ipynb
root = os.path.dirname(os.path.dirname(os.getcwd()))
# root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.append(root)

from server_minio_storage_connector import ServerStorageMinio



minio_config = {
    "access_key": "minioadmin",
    "secret_key": "minioadmin",
    "bucket_name": "test-bucket",
    # "endpoint_url": "http://localhost:9000"
    # "endpoint_url": "http://128.214.254.126:9000",
    # "endpoint_url": "http://localhost:9000",
    "endpoint_url": "http://192.168.10.234:9000",
    "region_name": "ap-southeast-2"
}


server_minio = ServerStorageMinio(minio_config= minio_config)

server_minio.create_bucket()
worker_id = "1234567890"

access_key, secret_key = server_minio.get_client_key(worker_id= worker_id)

print(access_key, secret_key)