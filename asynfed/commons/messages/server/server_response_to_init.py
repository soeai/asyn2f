from uuid import uuid4


class ResponseToInit:
    """
    Sample params:
        model_info: {
            "model_url": "model_name",
            "global_model_name": "model_version",
            "exchange_at": {"performance": 80,
                            "epoch": 100}
        }
        aws_info: {
            "access_key": "",
            "secret_key": "",
            "region_name": "asia-southeast-2",
        }
        queue_info: {
            training_exchange: "",
            monitor_queue: "",

        "model_exchange_at":{
            "performance": 0.35,
            "epoch": 3
        },
        }
    """
    def __init__(self, session_id, model_info: dict, storage_info: dict, queue_info: dict, exchange_at: dict, reconnect: bool):
        self.session_id = session_id
        self.model_info = model_info
        self.storage_info = storage_info
        self.queue_info = queue_info
        self.exchange_at = exchange_at 
        self.reconnect = reconnect

    def to_dict(self) -> dict:
        return self.__dict__