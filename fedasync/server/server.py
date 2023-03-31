import logging
from abc import abstractmethod, ABC
from time import sleep

from fedasync.commons.conf import StorageConfig
from fedasync.commons.messages.server_notify_model_to_client import ServerNotifyModelToClient
from fedasync.server.server_queue_manager import ServerConsumer, ServerProducer
from fedasync.server.server_storage_connector import ServerStorage
from fedasync.server.strategies import Strategy
from fedasync.server.worker_manager import WorkerManager
import threading

lock = threading.Lock()
LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class Server(ABC):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """

    def __init__(self, strategy: Strategy, t: int = 30) -> None:
        # Server variables
        self.t = t
        self.alpha: dict = {}
        self.strategy = strategy

        # Server's self.container
        self.server_access_key = 'minioadmin'
        self.server_secret_key = 'minioadmin'

        if StorageConfig.ACCESS_KEY == "" or StorageConfig.SECRET_KEY == "":
            StorageConfig.ACCESS_KEY = self.server_access_key
            StorageConfig.SECRET_KEY = self.server_secret_key

        self.worker_manager = WorkerManager()
        self.server_producer = ServerProducer()
        self.server_storage = ServerStorage()
        self.server_consumer = ServerConsumer(
            strategy=self.strategy,
            cloud_storage=self.server_storage,
            worker_manager=self.worker_manager
        )

    def run(self):

        # create 1 thread to listen on the queue.
        consuming_thread = threading.Thread(target=self.server_consumer.run,
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
                self.update()
                self.publish_global_model()

            if self.is_stop_condition():
                self.stop_listening()
                break

    def stop_listening(self):
        with lock:
            self.server_consumer.stop()

    def update(self):
        with lock:
            local_weights = self.worker_manager.get_all()
        self.strategy.aggregate(local_weights)

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
        self.server_producer.notify_global_model_to_client(msg.serialize())
