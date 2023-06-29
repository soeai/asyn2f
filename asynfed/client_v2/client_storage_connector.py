from asynfed.commons.utils import AWSConnector


class ClientStorage(AWSConnector):
    def __init__(self, aws_config):
        super().__init__(aws_config)

