#############################################################################################
# NOTE: do not directly modify config in this file, declare in the program file instead!##
#############################################################################################
import logging
import os

LOGGER = logging.getLogger(__name__)


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
    MONITOR_QUEUE: str = "monitor_queue"

    # Exchanges
    TRAINING_EXCHANGE: str = "training_exchange"

    # this folder is used to save local models
    TMP_LOCAL_MODEL_FOLDER = "./weights/local_weights/"
    TMP_GLOBAL_MODEL_FOLDER = "./weights/global_weights/"
    LOG_PATH = "./logs/"

    STORAGE_ACCESS_KEY = ""
    STORAGE_SECRET_KEY = ""
    STORAGE_BUCKET_NAME = ""
    STORAGE_REGION_NAME = 'ap-southeast-2'


def check_valid_config():
    LOGGER.info("Check config")
    for field in Config.__dict__:
        if Config.__dict__[field] == "" and "STORAGE_" not in field:
            raise Exception(f"{field} at {Config.__name__} cannot be empty!, please check again!")

    LOGGER.info("Config is valid!")


def prepare_folder():
    LOGGER.info("Create folder ...")
    if not os.path.exists(Config.TMP_GLOBAL_MODEL_FOLDER):
        os.makedirs(Config.TMP_GLOBAL_MODEL_FOLDER)
    if not os.path.exists(Config.TMP_LOCAL_MODEL_FOLDER):
        os.makedirs(Config.TMP_LOCAL_MODEL_FOLDER)
    if not os.path.exists(Config.LOG_PATH):
        os.makedirs(Config.LOG_PATH)


def init_config():
    LOGGER.info(f'\n\n\n Config: {Config.__class__.__dict__} \n\n\n')
    check_valid_config()
    prepare_folder()
    # Define logger
    LOG_FORMAT = '%(levelname) -10s %(asctime)s %(name) -30s %(funcName) -35s %(lineno) -5d: %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        # filename=f"{Config.LOG_PATH+'log.txt'}",
        # filemode='a',
        # datefmt='%H:%M:%S'
    )
