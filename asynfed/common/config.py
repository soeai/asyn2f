#############################################################################################
# NOTE: do not directly modify config in this file, declare in the program file instead!##
#############################################################################################
import logging
import os
from datetime import datetime

from .messages import MessageObject

LOGGER = logging.getLogger(__name__)


class MessageType:
    CLIENT_INIT_MESSAGE = "WORKER_INIT"
    CLIENT_NOTIFY_MESSAGE = "WORKER_NOTIFY"
    CLIENT_NOTIFY_EVALUATION = "WORKER_NOTIFY_EVALUATION"
    CLIENT_PING_MESSAGE = "WORKER_PING"
    CLIENT_REQUIRE_STOP = "WORKER_REQUIRE_STOP"

    SERVER_INIT_RESPONSE = "SERVER_INIT_RESP"
    SERVER_NOTIFY_MESSAGE = "SERVER_NOTIFY"
    SERVER_STOP_TRAINING = "SERVER_STOP_TRAINING"
    SERVER_PING_TO_CLIENT = "SERVER_PING_TO_WORKER"




class QueueConfig(MessageObject):
    def __init__(self, queue_name: str, queue_exchange: str, exchange_type: str, 
                 routing_key: str, endpoint: str, **kwargs):
        self.queue_name = queue_name
        self.queue_exchange = queue_exchange
        self.exchange_type = exchange_type
        self.routing_key = routing_key
        self.endpoint = endpoint
    

class LocalStoragePath():
    def __init__(self, root_folder: str, save_log= True):
        self.LOCAL_MODEL_ROOT_FOLDER = os.path.join(root_folder, "weights", "local_weights")
        self.GLOBAL_MODEL_ROOT_FOLDER = os.path.join(root_folder, "weights", "global_weights")
        self.LOG_FOLDER = os.path.join(root_folder, "logs")

        # create folder if not exist
        self._create_folder(self.LOCAL_MODEL_ROOT_FOLDER)
        self._create_folder(self.GLOBAL_MODEL_ROOT_FOLDER)
        self._create_folder(self.LOG_FOLDER)
        self._create_log_file(save_log= save_log)

    def _create_folder(self, folder_path: list):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    def _create_log_file(self, save_log= True):
        LOG_FORMAT = '%(levelname) -10s %(asctime)s %(name) -30s %(funcName) -35s %(lineno) -5d: %(message)s'
        if save_log:
            file_name = f"{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.log"
            file_path = os.path.join(self.LOG_FOLDER, file_name)

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


class CloudStoragePath():
    def __init__(self, global_model_root_folder: str, 
                 client_model_root_folder: str):
        self.GLOBAL_MODEL_ROOT_FOLDER = global_model_root_folder
        self.CLIENT_MODEL_ROOT_FOLDER = client_model_root_folder
