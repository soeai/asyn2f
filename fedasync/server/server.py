import os
from dotenv import load_dotenv
import logging
import uuid
from abc import abstractmethod
from time import sleep
from pika import BasicProperties
from fedasync.commons.conf import Config, RoutingRules, Config, check_valid_config, init_config
from fedasync.commons.messages.client_init_connect_to_server import ClientInit
from fedasync.commons.messages.client_notify_model_to_server import ClientNotifyModelToServer
from fedasync.commons.messages.server_init_response_to_client import ServerInitResponseToClient
from fedasync.commons.messages.server_notify_model_to_client import ServerNotifyModelToClient
from fedasync.commons.utils.queue_connector import QueueConnector
from fedasync.server.objects import Worker
from fedasync.server.server_storage_connector import ServerStorage
from fedasync.server.strategies import Strategy
from fedasync.server.worker_manager import WorkerManager
import threading

load_dotenv()

lock = threading.Lock()

LOGGER = logging.getLogger(__name__)


class Server(QueueConnector):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """

    def __init__(self, strategy: Strategy, t: int = 15) -> None:
        # Server variables
        super().__init__()
        self._t = t
        self._strategy = strategy
        # variables
        self._is_downloading = False
        self._is_new_global_model = False

        init_config()

        # NOTE: Any worker/server is forced to declare ServerConfig attributes before running.
        # if there is no key assign by the user => set default key for the storage ServerConfig.
        if Config.STORAGE_ACCESS_KEY == "" or Config.STORAGE_SECRET_KEY == "":
            # read access_key and secret_key from file .env
            Config.STORAGE_ACCESS_KEY = os.getenv('access_key')
            Config.STORAGE_SECRET_KEY = os.getenv('secret_key')

            if Config.STORAGE_ACCESS_KEY == "" or Config.STORAGE_SECRET_KEY == "":
                raise Exception("Add s3 AccessKey and  SecretKey please!")

        # Dependencies
        self._worker_manager: WorkerManager = WorkerManager()
        self._cloud_storage: ServerStorage = ServerStorage()

    def on_message(self, channel, method, properties: BasicProperties, body):

        if method.routing_key == RoutingRules.CLIENT_INIT_SEND_TO_SERVER:

            # Get message from Client
            client_init_message: ClientInit = ClientInit()
            client_init_message.deserialize(body.decode())
            LOGGER.info(f"client_msg: {client_init_message.__str__()} at {threading.current_thread()}")

            # Create worker and add to Worker Manager.
            worker_id = str(uuid.uuid4())
            new_worker = Worker(
                worker_id=worker_id,
                sys_info=client_init_message.sys_info,
                data_desc=client_init_message.data_desc,
                qod=client_init_message.qod
            )

            # Generate minio keys
            with lock:
                access_key, secret_key = self._cloud_storage.get_client_key(worker_id)

            model_name = self._cloud_storage.get_newest_global_model().split('.')[0]
            model_version = model_name.split('_')[1][1:]
            try:
                self._strategy.current_version = int(model_version)
            except Exception as e:
                logging.error(e)
                self._strategy.current_version = 0

            # Build response message
            response = ServerInitResponseToClient(
                session_id=client_init_message.session_id,
                client_id=new_worker.worker_id,
                model_url=self._cloud_storage.get_newest_global_model(),
                model_version=self._strategy.current_version,
                access_key=access_key,
                secret_key=secret_key,
                bucket_name=Config.STORAGE_BUCKET_NAME,
                region_name=Config.STORAGE_REGION_NAME,
                training_exchange=Config.TRAINING_EXCHANGE,
                monitor_queue=Config.MONITOR_QUEUE

            )
            LOGGER.info(f"server response: {response.__str__()} at {threading.current_thread()}")
            self.response_to_client_init_connect(response)

            # Add worker to Worker Manager.
            with lock:
                new_worker.access_key_id = access_key
                self._worker_manager.add_worker(new_worker)

        elif method.routing_key == RoutingRules.CLIENT_NOTIFY_MODEL_TO_SERVER:
            client_notify_message = ClientNotifyModelToServer()
            client_notify_message.deserialize(body.decode())
            print(f'Receive new model from client [{client_notify_message.client_id}]!')

            # Download model!
            with lock:
                self._cloud_storage.download(bucket_name='fedasyn',
                                             remote_file_path=client_notify_message.weight_file,
                                             local_file_path=Config.TMP_LOCAL_MODEL_FOLDER + client_notify_message.model_id)
                self._worker_manager.add_local_update(client_notify_message)

    def setup(self):
        # Declare exchange, queue, binding.
        self._channel.exchange_declare(exchange=Config.TRAINING_EXCHANGE, exchange_type=self.EXCHANGE_TYPE)
        self._channel.queue_declare(queue=Config.QUEUE_NAME)
        self._channel.queue_bind(
            Config.QUEUE_NAME,
            Config.TRAINING_EXCHANGE,
            RoutingRules.CLIENT_NOTIFY_MODEL_TO_SERVER
        )
        self._channel.queue_bind(
            Config.QUEUE_NAME,
            Config.TRAINING_EXCHANGE,
            RoutingRules.CLIENT_INIT_SEND_TO_SERVER
        )
        self.start_consuming()

    def notify_global_model_to_client(self, message):
        # Send notify message to client.
        self._channel.basic_publish(
            Config.TRAINING_EXCHANGE,
            RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT,
            message.serialize()
        )

    def response_to_client_init_connect(self, message):
        # Send response message to client.
        self._channel.basic_publish(
            Config.TRAINING_EXCHANGE,
            RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT,
            message.serialize()
        )

    def run(self):

        # create 1 thread to listen on the queue.
        consuming_thread = threading.Thread(target=self.run_queue,
                                            name="fedasync_server_consuming_thread")

        # run the consuming thread!.
        consuming_thread.start()

        while not self.is_stop_condition() and not self._closing:
            with lock:
                n_local_updates = len(self._worker_manager.get_completed_workers())
            if n_local_updates == 0:
                print(f'No local update found, sleep for {self._t} seconds...')
                # Sleep for t seconds.
                sleep(self._t)
            elif n_local_updates > 0:
                print(f'Found {n_local_updates} local update(s)')
                print('Start update global model')
                self.update()
                self.publish_global_model()

                # Clear worker queue after aggregation.
                self._worker_manager.update_worker_after_training()

        self.stop()

    def update(self):
        self._strategy.aggregate(self._worker_manager)

    @abstractmethod
    def is_stop_condition(self):
        return False

    def publish_global_model(self):
        print('Publish global model (sv notify model to client)')
        local_filename = f'{Config.TMP_GLOBAL_MODEL_FOLDER}{self._strategy.model_id}_v{self._strategy.current_version}.pkl'
        remote_filename = f'global-models/{self._strategy.model_id}_v{self._strategy.current_version}.pkl'
        self._cloud_storage.upload(local_filename, remote_filename, 'fedasyn')
        # Construct message
        msg = ServerNotifyModelToClient(
            model_id=self._strategy.model_id,
            chosen_id=[],
            global_model_name=f'{self._strategy.model_id}_v{self._strategy.current_version}.pkl',
            global_model_version=self._strategy.current_version,
            avg_loss=self._strategy.avg_loss,
            global_model_update_data_size=self._strategy.global_model_update_data_size
        )
        # Send message
        self.notify_global_model_to_client(msg)
