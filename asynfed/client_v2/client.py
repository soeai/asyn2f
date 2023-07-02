import os, sys

from asynfed.commons.utils.time_ultils import time_now
root = os.path.dirname(os.path.dirname(os.getcwd()))
sys.path.append(root)
import json
import logging
import os
import threading
import uuid
from time import sleep
from abc import abstractmethod
from asynfed.client_v2.client_storage_connector import ClientStorage
from asynfed.client_v2.messages import init_connection
from asynfed.commons.conf import RoutingRules, Config, init_config
from asynfed.commons.messages import message_v2
from asynfed.commons.messages.client_init_connect_to_server import SysInfo
from asynfed.commons.utils.queue_consumer import AmqpConsumer
from asynfed.commons.utils.queue_producer import AmqpProducer
import concurrent.futures
thread_pool_ref = concurrent.futures.ThreadPoolExecutor
import pause
from apscheduler.schedulers.background import BackgroundScheduler

from asynfed.client_v2.ModelWrapper import ModelWrapper

LOGGER = logging.getLogger(__name__)

lock = threading.Lock()

class Client(object):
    def __init__(self, model: ModelWrapper, config):
        self.config = config

        # Dependencies
        self._global_chosen_list = None
        self._save_global_avg_qod = None
        self._save_global_avg_loss = None
        self._save_global_model_update_data_size = None
        self._save_global_model_version = None

        self.model = model
        self._local_data_size = self.model.data_size
        self._local_qod = self.model.qod
        self._train_acc = 0.0
        self._train_loss = 0.0

        # for updating new global model
        self._previous_global_version = 0
        self._current_global_version = 0
        self._received_global_version = 0

        self._global_model_name = None

        self._local_epoch = 0

        # merging process
        self._global_avg_loss = None
        self._global_avg_qod = None
        self._global_model_update_data_size = None

        # variables.
        if self.config['client_id'] is None:
            self._client_id = str(uuid.uuid4())
        else:
            self._client_id = self.config['client_id']
        self._is_training = False
        self._session_id = ""
        self._new_model_flag = False
        self._is_connected = False

        self.config['queue_consumer']['queue_name'] = "queue_" + self._client_id

        # Initialize profile for client
        if not os.path.exists("profile.json"):
            self.create_profile()
        else:
            self.load_profile()

        # self.log: bool = True
        Config.TRAINING_EXCHANGE = "asdasd"

        init_config("client")

        # self.aws_thread = threading.Thread(target=self._handle_aws)
        self.thread_consumer = threading.Thread(target=self._start_consumer)
        self.queue_consumer = AmqpConsumer(self.config['queue_consumer'], self)
        self.queue_producer = AmqpProducer(self.config['queue_producer'])

        LOGGER.info(f'\n\nClient Id: {self._client_id}'
                    f'\n\tQueue In : {self.config["queue_consumer"]}'
                    f'\n\tQueue Out : {self.config["queue_producer"]}'
                    f'\n\n')

        self._send_init_message()

    def on_download(self, result):
        if result:
            self._new_model_flag = True
            LOGGER.info(f"Successfully downloaded new global model, version {self._global_model_version}")
        else:
            print("Download model failed. Passed this version!")

    def on_upload(self, result):
        pass

    def on_message_received(self, ch, method, props, body):
        msg_received = message_v2.MessageV2.serialize(body.decode('utf-8'))
        content = msg_received['content']

        # IF message come from SERVER_INIT_RESPONSE_TO_CLIENT
        if msg_received['headers']['message_type'] == Config.SERVER_INIT_RESPONSE and not self._is_connected:
            # message_v2.MessageV2.print_message(msg_received)
            print('SERVER INIT RESPONSE', msg_received)
            if content['reconnect'] is True:
                print("Reconnect to server.")

            self._session_id = content['session_id']
            self._global_model_name = content['model_info']['global_model_name']
            self._received_global_version = content['model_info']['model_version']
            # print("*" * 20)
            # print(self._current_global_version)
            # print("*" * 20)
            self._storage_connector = ClientStorage(content['aws_info'])
            self._is_connected = True

            # Check for new global model version.
            if self._current_global_version < self._received_global_version:
                self._current_global_version = self._received_global_version
                LOGGER.info("Detect new global version.")
                local_path = f"{Config.TMP_GLOBAL_MODEL_FOLDER}{self._global_model_name}"

                while True:
                    if self._storage_connector.download(remote_file_path=content['model_info']['model_url'], 
                                                    local_file_path=local_path):
                        break
                    print("Download model failed. Retry in 5 seconds.")
                    sleep(5)

            self.update_profile()
            self.start_training_thread()

        elif msg_received['headers']['message_type'] == Config.SERVER_NOTIFY_MESSAGE and self._is_connected:
            # download model.

            print("*" * 20)
            print('SERVER NOTIFY MESSAGE', msg_received)
            print("*" * 20)
            with lock:
                # ----- receive and load global message ----
                self._global_chosen_list = content['chosen_id']

                # update latest model info
                self._global_model_name = content['global_model_name']
                self._received_global_version = content['global_model_version']

                # global info for merging process
                self._global_model_update_data_size = content['global_model_update_data_size']
                self._global_avg_loss = content['avg_loss']
                self._global_avg_qod = content['avg_qod']
                print("*" * 20)
                print(
                    f"global data_size, global avg loss, global avg qod: {self._global_model_update_data_size}, {self._global_avg_loss}, {self._global_avg_qod}")
                print("*" * 20)

                # save the previous local version of the global model to log it to file
                self._previous_global_version = self._current_global_version
                # update local version (the latest global model that the client have)
                self._current_global_version = self._received_global_version

                remote_path = f'global-models/{content["model_id"]}_v{self._current_global_version}.pkl'
                local_path = f'{Config.TMP_GLOBAL_MODEL_FOLDER}{content["model_id"]}_v{self._current_global_version}.pkl'

                LOGGER.info("Downloading new global model............")

                while True:
                    if self._storage_connector.download(remote_file_path=self._global_model_name,
                                                        local_file_path=local_path):
                        break
                    print("Download model failed. Retry in 5 seconds.")
                    sleep(5)

                LOGGER.info(f"Successfully downloaded new global model, version {self._current_global_version}")

                # # change the flag to true.
                self._new_model_flag = True


    @abstractmethod
    def train(self):
        pass

    def create_message(self):
        data = {
            "session_id": self._session_id,
            "client_id": self._client_id,
            "global_model_name": self._global_model_name,
            "local_epoch": self._local_epoch - 1,
            "local_qod": self._local_qod,
            "save_global_model_version": self._current_global_version,
            "save_global_model_update_data_size": self._global_model_update_data_size,
            "save_global_avg_loss": self._global_avg_loss,
            "save_global_avg_qod": self._global_avg_qod,

            # "local_data_size": self._local_data_size,
            # "local_qod": self._local_qod,
            # "train_loss": self._train_loss,
        }
        return data

    def create_profile(self):
        data = self.create_message()
        with open("profile.json", "w") as outfile:
            json.dump(data, outfile)

    def update_profile(self):
        data = self.create_message()
        with open("profile.json", "w") as outfile:
            json.dump(data, outfile)

    # load client information from profile.json function
    def load_profile(self):
        try:
            with open("profile.json") as json_file:
                data = json.load(json_file)
                self._session_id = data["session_id"]
                self._client_id = data["client_id"]
                self._global_model_name = data["global_model_name"]
                self._local_epoch = data["local_epoch"]
                self._local_qod = data["local_qod"]

                self._save_global_model_version = data["save_global_model_version"]
                self._save_global_model_update_data_size = data["save_global_model_update_data_size"]
                self._save_global_avg_loss = data["save_global_avg_loss"]
                self._save_global_avg_qod = data["save_global_avg_qod"]

                # self._local_data_size = data["local_data_size"]
                # self._train_loss = data["train_loss"]
        except Exception as e:
            print(e)


    def _send_init_message(self):
        data_description = {
            'data_size': self._local_data_size,
            'qod': self._local_qod,
        }
        message = message_v2.MessageV2(
            headers={'timestamp': time_now(), 'message_type': Config.CLIENT_INIT_MESSAGE, 'session_id': self._session_id, 'client_id': self._client_id},
            content=init_connection.InitConnection(
                data_description=data_description,
            )
        ).to_json()
        self.queue_producer.send_data(message)
        

    def _start_consumer(self):
        self.queue_consumer.start()

    # Run the client
    def start(self):
        self.thread_consumer.start()

    def start_training_thread(self):
        LOGGER.info("Start training thread.")
        training_thread = threading.Thread(
            target=self.train,
            name="client_training_thread")

        self._is_training = True
        training_thread.start()


# if __name__ == '__main__':
#     scheduler = BackgroundScheduler()

# # your code goes here


#     config = {
#         "client_id": "002",
#         "queue_consumer": {
#             'exchange_name': 'asynfl_exchange',
#             'exchange_type': 'topic',
#             'queue_name': 'server_queue',
#             'routing_key': 'client.#',
#             'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu'
#         },
#         "queue_producer": {
#             'exchange_name': 'asynfl_exchange',
#             'exchange_type': 'topic',
#             'queue_name': 'server_consumer',
#             'routing_key': 'server.#',
#             'end_point': "amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu"
#         }
#     }
#     class NewClient(Client):
#         def train(self):
#             pass
#     client = NewClient(config)
#     client.start()

#     scheduler.start()
#     pause.days(1) # or it can anything as per your need
