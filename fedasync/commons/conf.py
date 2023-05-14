#############################################################################################
# NOTE: do not directly modify config in this file, declare in the program file instead!##
#############################################################################################

class RoutingRules:
    # at ClientModel Queue
    CLIENT_INIT_SEND_TO_SERVER: str = "client.init.send.to.server"
    CLIENT_NOTIFY_MODEL_TO_SERVER: str = "client.notify.update"

    # at Server Queue
    SERVER_INIT_RESPONSE_TO_CLIENT: str = "server.init.reply"
    SERVER_NOTIFY_MODEL_TO_CLIENT: str = "server.notify.global.model.to.client"


class StorageConfig:
    STORAGE_URL: str = ""
    ACCESS_KEY = ""
    SECRET_KEY = ""
    BUCKET_NAME = ""
    REGION_NAME = 'ap-southeast-2'


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
    TMP_GLOBAL_MODEL_FOLDER = ""
    TMP_LOCAL_MODEL_FOLDER = ""

    STORAGE_CONFIG = StorageConfig


def check_valid_config(config_class):
    for field in config_class.__class__.__dict__:
        if StorageConfig.__class__.__dict__[field] == "" and field != "STORAGE_CONFIG":
            raise Exception(f"{field} at {config_class.__name__} cannot be empty!, please check again!")
