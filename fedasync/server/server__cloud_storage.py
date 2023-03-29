from fedasync.commons.utils.cloud_storage_connector import MinioConnector


class ServerCloudStorage(MinioConnector):
    def __init__(self, access_key, secret_key, uuid):
        super().__init__(access_key, secret_key, uuid)

    def generate_keys(self):
        access_key, secret_key = ""
        return access_key, secret_key
