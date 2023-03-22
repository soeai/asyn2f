from fedasync.commons.messages.message import Message


class ClientNotifyModelToServer(Message):

    def __init__(self, message):
        self.client_id =  ""
        self.model_id =  ""
        self.global_model_version_used =  1
        self.timestamp =  1213214
        self.loss_value =  1.42
        self.link =  "minio/model1"
        self.performance =  ""
        self.batch_size =  ""

        # Run deserialize message function.
        self.deserialize(message)





