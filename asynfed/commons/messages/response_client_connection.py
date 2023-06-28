class ResponseClientConnection:
    def __init__(self, client_profile, storage_info, model_info, queue_info):
        """
        Sample
        {
            "client_profile": {
                "client_identifier": "client_1",
                "session_id": "session_1",
                "client_id": "client_1"
            },
            "storage": {
                access_key: "access_key",
                secret_key: "secret_key",
                bucket_name: "bucket_name",
                region_name: "region_name",
            },
            "model_info": {
                "global_model_name": "global_model_name",
                "model_url": "model_url",
                "model_version": "model_version"
            },
            "queue_info": {
                "monitor_queue": "monitor_queue",
                "training_exchange": "training_exchange"
            }

        """
        self.client_profile = client_profile
        self.queue_info = queue_info
        self.storage_info = storage_info
        self.model_info = model_info
