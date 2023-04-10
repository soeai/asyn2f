from fedasync.commons.messages.message import Message


class ClientNotifyModelToServer(Message):

    def __init__(self, message=None):
        self.client_id = ""
        self.model_id = ""
        self.global_model_version_used = 1
        self.timestamp = 1213214
        self.loss_value = 1.42
        self.weight_file = "local_version_v1.pickle"
        self.performance = 0.0
        self.batch_size = 0.0
        self.alpha = 0.0

        # Run deserialize message function.
        self.deserialize(message)
