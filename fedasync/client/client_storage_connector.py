from fedasync.commons.conf import StorageConfig
from fedasync.commons.utils.cloud_storage_connector import MinioConnector


class ClientStorage(MinioConnector):
    def __init__(self, access_key, secret_key, client_id):
        super().__init__(access_key, secret_key)
        self.client_id = client_id

    def get_model(self, model_version: str):
        self.download('global-models', model_version)

    def upload_local_model(self, file_path: str):
        self.upload(self.client_id, file_path)

