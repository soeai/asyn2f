class ResponseConnection:
    """
    Sample params:
        model_info: {
            "model_url": "model_name",
            "global_model_name": "model_version",
        }
        aws_info: {
            "access_key": "",
            "secret_key": "",
            "region_name": "asia-southeast-2",
        }
        queue_info: {
            training_exchange: "",
            monitor_queue: "",
        }
    """
    def __init__(self, model_info: dict, aws_info: dict, queue_info: dict):
        self.model_info = model_info
        self.aws_info = aws_info
        self.queue_info = queue_info
