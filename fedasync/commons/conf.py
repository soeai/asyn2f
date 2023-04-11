class RoutingRules:
    # at ClientModel Queue
    CLIENT_INIT_SEND_TO_SERVER: str = "client.init.send.to.server"
    CLIENT_NOTIFY_MODEL_TO_SERVER: str = "client.notify.update"

    # at Server Queue
    SERVER_INIT_RESPONSE_TO_CLIENT: str = "server.init.reply"
    SERVER_NOTIFY_MODEL_TO_CLIENT: str = "server.notify.global.model.to.client"


class Config:
    """
    Server config here!
    """
    # Queue name
    QUEUE_URL: str = "amqp://guest:guest@localhost:5672/%2F"
    QUEUE_NAME: str = ""
    MONITOR_QUEUE: str = ""

    # Exchanges
    TRAINING_EXCHANGE: str = "training_exchange"

    # this folder is used to save local models
    TMP_GLOBAL_MODEL_FOLDER = "./data/global_weights"
    TMP_LOCAL_MODEL_FOLDER = "./data/local_weights"


class StorageConfig:
    STORAGE_URL: str = ""
    ACCESS_KEY = ""
    SECRET_KEY = ""
    BUCKET_NAME = ""
