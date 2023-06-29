import json
import logging
import os
import threading
import uuid
from time import sleep
from abc import abstractmethod
from asynfed.client.client_storage_connector import ClientStorage
from asynfed.commons.conf import RoutingRules, Config, init_config
from asynfed.commons.messages import ClientInit, ServerNotifyModelToClient, ServerInitResponseToClient
from asynfed.commons.messages.client_init_connect_to_server import SysInfo
from asynfed.commons.utils.queue_consumer import AmqpConsumer
from asynfed.commons.utils.queue_producer import AmqpProducer

LOGGER = logging.getLogger(__name__)

lock = threading.Lock()


class Client(object):
    def __init__(self, config):
        # config structure
        # {
        #     "client_id": "",
        #     "queue_consumer": {
        #             'exchange_name': 'asynfl_exchange',
        #             'exchange_type': 'topic',
        #             'routing_key': 'server.#',
        #             'end_point': ''},
        #     "queue_producer": {
        #              'queue_name': 'client_queue',
        #             'exchange_name': 'test_exchange',
        #             'exchange_type': 'topic',
        #             'routing_key': 'client.#',
        #             'end_point': ""}
        # }
        self.config = config

        # Dependencies
        self._global_chosen_list = None
        self._save_global_avg_qod = None
        self._save_global_avg_loss = None
        self._save_global_model_update_data_size = None
        self._save_global_model_version = None
        self._local_data_size = 0
        self._local_qod = 0.0
        self._train_loss = 0.0

        self._previous_local_version = 0
        self._current_local_version = 0

        self._global_model_version = None

        self._global_model_name = None
        self._storage_connector = None

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
        self._is_registered = False

        self.config['queue_consumer']['queue_name'] = "queue_" + self._client_id

        # if there is no profile.json file, then create a new one.
        if not os.path.exists("profile.json"):
            self.create_profile()
        else:
            self.load_profile()

        self.log: bool = True

        init_config("client")

        self.thread_consumer = threading.Thread(target=self._start_consumer)
        self.queue_concumer = AmqpConsumer(self.config['queue_consumer'], self)
        self.queue_producer = AmqpProducer(self.config['queue_producer'])

        LOGGER.info(f'\n\nClient Id: {self._client_id}'
                    f'\n\tQueue In : {self.config["queue_consumer"]}'
                    f'\n\tQueue Out : {self.config["queue_producer"]}'
                    f'\n\n')

    def on_download(self, result):
        if result:
            self._new_model_flag = True
            LOGGER.info(f"Successfully downloaded new global model, version {self._global_model_version}")
        else:
            print("Download model failed. Passed this version!")

    def on_upload(self, result):
        pass

    def on_message_handling(self, ch, method, props, body):
        # If message come from routing SERVER_INIT_RESPONSE_TO_CLIENT then save the model id.
        receive_msg = json.loads(bytes.decode(body))

        if receive_msg['type'] == Config.SERVER_INIT_RESPONSE:
            message = ServerInitResponseToClient()
            message.deserialize(receive_msg['content'])

            LOGGER.info(message.__dict__)

            # Get only the message that server reply to it base on the session_id
            if self._client_id == message.client_id:
                # set client property from message
                if self._session_id == message.session_id:
                    # welcome back message
                    LOGGER.info(
                        f"Welcome back {message.client_id} | session_id: {message.session_id}"
                    )
                else:
                    # registration message
                    LOGGER.info(
                        f"Client {message.client_id} is succesfully registered | session_id: {message.session_id}"
                    )
                self._session_id = message.session_id
                self._client_id = message.client_id
                self._global_model_name = message.model_url
                self._global_model_version = message.model_version

                LOGGER.info(
                    f'Init connection to the server successfully | access_key: {message.access_key} | secret_key: {message.secret_key} | model_url: {message.model_url}')
                Config.STORAGE_ACCESS_KEY = message.access_key
                Config.STORAGE_SECRET_KEY = message.secret_key
                Config.STORAGE_REGION_NAME = message.region_name
                Config.STORAGE_BUCKET_NAME = message.bucket_name
                Config.MONITOR_QUEUE = message.monitor_queue

                self._storage_connector = ClientStorage()

                LOGGER.info(
                    f"Init connection to the server successfully | access_key: {message.access_key} | secret_key: {message.secret_key} | model_url: {message.model_url}"
                )
                self._is_registered = True

                # if local model version is smaller than the global model version and client's id is in the chosen ids
                # for the time it back to the training process
                if self._current_local_version < self._global_model_version:
                    LOGGER.info("Detect new global version.")

                    filename = self._global_model_name.split("/")[-1]
                    local_path = f"{Config.TMP_GLOBAL_MODEL_FOLDER}{filename}"

                    # while True:
                    #     if \
                    self._storage_connector.download(
                        remote_file_path=self._global_model_name,
                        local_file_path=local_path)
                    #     break
                    # print("Download model failed. Retry in 5 seconds.")
                    # sleep(5)

                    # start 1 thread to train model.
                    self.update_profile()
                    self.train()
                    # self.start_training_thread()

        elif (
                receive_msg['tyoe'] == Config.SERVER_NOTIFY_MESSAGE
                and self._is_registered
        ):
            # download model.
            msg = ServerNotifyModelToClient()
            msg.deserialize(receive_msg['content'])

            LOGGER.info("Receive global model notify............")
            print("*" * 20)
            print(msg)
            print("*" * 20)
            with lock:
                # ----- receive and load global message ----
                self._global_chosen_list = msg.chosen_id

                # update latest model info
                self._global_model_name = msg.global_model_name
                self._global_model_version = msg.global_model_version

                # global info for merging process
                self._global_model_update_data_size = msg.global_model_update_data_size
                self._global_avg_loss = msg.avg_loss
                self._global_avg_qod = msg.avg_qod
                print("*" * 20)
                print(
                    f"global data_size, global avg loss, global avg qod: {self._global_model_update_data_size}, {self._global_avg_loss}, {self._global_avg_qod}")
                print("*" * 20)

                # save the previous local version of the global model to log it to file
                self._previous_local_version = self._current_local_version
                # update local version (the latest global model that the client have)
                self._current_local_version = self._global_model_version

                remote_path = f'global-models/{msg.model_id}_v{self._global_model_version}.pkl'
                local_path = f'{Config.TMP_GLOBAL_MODEL_FOLDER}{msg.model_id}_v{self._global_model_version}.pkl'

                LOGGER.info("Downloading new global model............")
                # while True:
                #     if \
                self._storage_connector.download(remote_file_path=remote_path,
                                                 local_file_path=local_path)
                #     break
                # print("Download model failed. Retry in 5 seconds.")
                # sleep(5)
                # LOGGER.info(f"Successfully downloaded new global model, version {self._global_model_version}")

                # # change the flag to true.
                # self._new_model_flag = True

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
            "save_global_model_version": self._global_model_version,
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

    def notify_model_to_server(self, message):
        self.queue_producer.send_data(
            {"type": Config.CLIENT_NOTIFY_MESSAGE,
             "content": message.serialize()}
        )

    def init_connect_to_server(self, message):
        self.queue_producer.send_data(
            {"type": Config.CLIENT_INIT_MESSAGE,
             "content": message.serialize()})

    def publish_init_message(self, data_size=10000, qod=0.2):
        message = ClientInit(
            session_id=self._session_id,
            client_id=self._client_id,
            sys_info=SysInfo(),
            data_size=data_size,
            qod=qod
        )
        print("-" * 20)
        print("Init message of client")
        print(message)
        print("-" * 20)
        self.init_connect_to_server(message.serialize())

    def _start_consumer(self):
        self.queue_concumer.start()

    # Run the client
    def start(self):
        self.thread_consumer.start()

    # def start_training_thread(self):
    #     if not self._is_training:
    #         LOGGER.info("Start training thread.")
    #         training_thread = threading.Thread(
    #             target=self.train,
    #             name="client_training_thread")
    #
    #         self._is_training = True
    #         training_thread.start()
