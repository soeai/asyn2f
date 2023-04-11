import logging
import uuid
from abc import abstractmethod
from time import sleep
from pika import BasicProperties
from fedasync.commons.conf import StorageConfig, RoutingRules, Config
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

lock = threading.Lock()
LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class Server(QueueConnector):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """

    def __init__(self, strategy: Strategy, t: int = 30, server_access_key='minioadmin', server_secret_key='minioadmin') -> None:
        # Server variables
        super().__init__()
        self.t = t
        self.strategy = strategy
        # variables
        self.is_downloading = False
        self.is_new_global_model = False

        # Server account for minio by default.
        self.server_access_key = server_access_key
        self.server_secret_key = server_secret_key

        # if there is no key assign by the user => set default key for the storage config.
        if StorageConfig.ACCESS_KEY == "" or StorageConfig.SECRET_KEY == "":
            StorageConfig.ACCESS_KEY = self.server_access_key
            StorageConfig.SECRET_KEY = self.server_secret_key

        # Dependencies
        self.worker_manager: WorkerManager = WorkerManager()
        self.cloud_storage: ServerStorage = ServerStorage()

    def on_message(self, channel, method, properties: BasicProperties, body):

        if method.routing_key == RoutingRules.CLIENT_INIT_SEND_TO_SERVER:

            # get message and convert it
            client_init_message: ClientInit = ClientInit(body.decode())
            LOGGER.info(f"client_msg: {client_init_message.__str__()} at {threading.current_thread()}")

            # create worker and add worker to manager.
            new_id = str(uuid.uuid4())
            new_worker = Worker(
                new_id,
                client_init_message.sys_info,
                client_init_message.data_desc,
                client_init_message.qod
            )

            # Build response message
            response = ServerInitResponseToClient()
            response.session_id = client_init_message.session_id
            response.client_id = new_worker.uuid
            response.model_url = self.cloud_storage.get_newest_global_model()
            response.model_version = self.strategy.current_version
            # generate minio keys
            with lock:
                response.access_key, response.secret_key = self.cloud_storage.generate_keys(new_id, response.session_id)
                LOGGER.info("Failed here")

            LOGGER.info(f"server response: {response.__str__()} at {threading.current_thread()}")

            self.response_to_client_init_connect(response)

            #  add to worker.
            with lock:
                self.worker_manager.add_worker(new_worker)
                number_of_online_workers = self.worker_manager.total()

            if number_of_online_workers > 1:
                # construct message.
                msg = ServerNotifyModelToClient()
                msg.model_id = self.strategy.model_id
                msg.chosen_id = []
                msg.global_model_name = f"global_model_{self.strategy.current_version}"
                msg.global_model_version = msg.model_id
                msg.avg_loss = self.strategy.avg_loss
                msg.timestamp = 0
                msg.global_model_update_data_size = self.strategy.global_model_update_data_size

                self.notify_global_model_to_client(message=msg)

        elif method.routing_key == RoutingRules.CLIENT_NOTIFY_MODEL_TO_SERVER:
            # download local model.
            client_noty_message = ClientNotifyModelToServer(body.decode())

            # download model!
            with lock:
                self.cloud_storage.download(f'{client_noty_message.client_id}/{client_noty_message.weight_file}')
                self.worker_manager.add_local_update(client_noty_message)

            # print out
            LOGGER.info(f"New model from {client_noty_message.client_id} is successfully downloaded! ")

    def setup(self):
        # declare exchange.
        self._channel.exchange_declare(exchange=Config.TRAINING_EXCHANGE, exchange_type=self.EXCHANGE_TYPE)

        # declare queue
        self._channel.queue_declare(queue=Config.QUEUE_NAME)

        # binding.
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
        self._channel.basic_publish(
            Config.TRAINING_EXCHANGE,
            RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT,
            message.serialize()
        )

    def response_to_client_init_connect(self, message):
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

        while True:
            with lock:
                n_local_updates = self.worker_manager.get_n_local_update(self.strategy.current_version)
                LOGGER.info(f"Check, n_local_update = {n_local_updates}")
            if n_local_updates == 0:
                sleep(self.t)
            elif n_local_updates > 0:
                print('publish global model')
                self.update()

                if self.is_stop_condition():
                    self.stop()
                    break

                self.publish_global_model()
                # Clear worker queue after aggregation.
                self.worker_manager.worker_update_queue.clear()

    def update(self):
        with lock:
            workers = self.worker_manager.get_all()

        self.strategy.aggregate(workers, self.worker_manager.worker_update_queue)

    @abstractmethod
    def is_stop_condition(self):
        return False

    def publish_global_model(self):
        # Construct message
        msg = ServerNotifyModelToClient()
        msg.model_id = self.strategy.model_id
        msg.global_model_name = self.strategy.get_global_model_filename()
        msg.global_model_version = self.strategy.current_version
        msg.avg_loss = self.strategy.avg_loss
        msg.chosen_id = []
        msg.global_model_update_data_size = self.strategy.global_model_update_data_size

        # Send message
        with lock:
            self.notify_global_model_to_client(msg)
