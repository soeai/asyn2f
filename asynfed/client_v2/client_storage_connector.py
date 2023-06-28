from asynfed.commons.utils import AWSConnector


class ClientStorage(AWSConnector):
    def __init__(self, access_key, secret_key, bucket_name, region, parent=None):
        super().__init__(access_key, secret_key, bucket_name, region, parent)

