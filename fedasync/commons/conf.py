class RoutingRules:
    """
    define routing key here!
    """
    # at Client Queue
    CLIENT_INIT_SEND_TO_SERVER: str = "client.init.send.to.server"
    CLIENT_NOTIFY_MODEL_TO_SERVER: str = "client.notify.update"

    # at Server Queue
    SERVER_INIT_RESPONSE_TO_CLIENT: str = "server.init.reply"
    SERVER_NOTIFY_MODEL_TO_CLIENT: str = "server.notify.global.model.to.client"


class ServerConfig:
    """
    Server config here!
    """
    # Queue name
    QUEUE_URL: str = ""
    SERVER_QUEUE: str = "server_queue"
    MONITOR_QUEUE: str = "monitor_queue"

    # Exchanges
    TRAINING_EXCHANGE: str = "training_exchange"

    # this folder is used to save local models
    TMP_LOCAL_MODEL_FOLDER = ""


class ClientConfig:
    """
    Client config here!
    """
    CLIENT_QUEUE: str = ""
    TRAINING_EXCHANGE: str = ""
    QUEUE_URL: str = ""

    # this folder is used to save the global model in local
    TMP_GLOBAL_MODEL_FOLDER = ""


class StorageConfig:
    """
    storage config here!
    """

    URL: str = ""
    ACCESS_KEY = ""
    PRIVATE_KEY = ""
