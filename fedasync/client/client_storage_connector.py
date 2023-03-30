from fedasync.commons.utils.cloud_storage_connector import MinioConnector


class ClientStorage(MinioConnector):
    def __init__(self,  access_key, secret_key, uuid):
        super().__init__(access_key, secret_key)
        self.uuid = uuid

    def get_model(self, model_version: str):
        self.download('global-models', model_version)

    def upload_local_model(self, file_path: str):
        self.upload(self.uuid, file_path)

if __name__ == '__main__':
    client_storage = ClientStorage('696c1fdf-ee73-4d0c-b883-ec8553fb40e7', '415bdb6e-fe30-427b-82f8-73bdc62e759e', '696c1fdf-ee73-4d0c-b883-ec8553fb40e7')
    client_storage.get_model('coco_sample.png')