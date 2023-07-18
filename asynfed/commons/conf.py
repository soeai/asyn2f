#############################################################################################
# NOTE: do not directly modify config in this file, declare in the program file instead!##
#############################################################################################
import logging
import os

LOGGER = logging.getLogger(__name__)

class Config:
    """
    Server config here!
    """
    # Queue name
    QUEUE_URL: str = "amqp://guest:guest@195.148.22.62:5672"
    QUEUE_NAME: str = ""
    MONITOR_QUEUE: str = "any"


    CLIENT_INIT_MESSAGE = "client_init"
    CLIENT_NOTIFY_MESSAGE = "client_notify"
    CLIENT_NOTIFY_EVALUATION = "client.notify.evaluation"
    CLIENT_PING_MESSAGE = "client_ping"
    CLIENT_REQUIRE_STOP = "client_require_stop"
    SERVER_INIT_RESPONSE = "server_init_resp"
    SERVER_NOTIFY_MESSAGE = "server_notify"
    SERVER_STOP_TRAINING = "server_stop_training"
    SERVER_PING_TO_CLIENT = "server_ping_to_client"


    # this folder is used to save weights
    # user must define these location in run file
    TMP_LOCAL_MODEL_FOLDER = os.path.join("weights", "local_weights")
    TMP_GLOBAL_MODEL_FOLDER = os.path.join("weights", "global_weights")
    LOG_PATH = "logs"

    # Cloud storage bucket information.
    STORAGE_ACCESS_KEY = ""
    STORAGE_SECRET_KEY = ""
    STORAGE_BUCKET_NAME = ""
    STORAGE_REGION_NAME = 'ap-southeast-2'

    # config sleep time for tensorflow small client model
    SLEEPING_TIME = 10
    TRACKING_POINT = 5000
    BATCH_SIZE=128

    EPOCH = 5
    DELTA_TIME = 15


def check_valid_config(side="server"):
    LOGGER.info("Check config")
    for field in Config.__dict__:
        if side == "server":
            if Config.__dict__[field] == "" and field != "MONITOR_QUEUE":
                raise Exception(f"{field} at {Config.__name__} cannot be empty!, please check again!")
        elif side == "client":
            if Config.__dict__[field] == "" and field not in ["QUEUE_NAME", "QUEUE_URL"] and "STORAGE_" not in field:
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


def init_config(side, save_log=True):
    from datetime import datetime
    # check_valid_config(side)
    prepare_folder()
    
    if not os.path.exists(Config.LOG_PATH):
        os.makedirs(Config.LOG_PATH)

    LOG_FORMAT = '%(levelname) -10s %(asctime)s %(name) -30s %(funcName) -35s %(lineno) -5d: %(message)s'

    if save_log:
        file_name = f"{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.log"
        file_path = os.path.join(Config.LOG_PATH, file_name)
        logging.basicConfig(
            level=logging.INFO,
            format=LOG_FORMAT,
            filename=file_path,
            filemode='a',
            datefmt='%H:%M:%S'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format=LOG_FORMAT,
            datefmt='%H:%M:%S'
        )
