import uuid

from pika import BasicProperties

from fedasync.commons.messages.client_init_connect_to_server import ClientInit
from fedasync.commons.messages.client_notify_model_to_server import ClientNotifyModelToServer
from fedasync.commons.messages.server_init_response_to_client import ServerInitResponseToClient
from fedasync.commons.messages.server_notify_model_to_client import ServerNotifyModelToClient
from fedasync.commons.utils.consumer import Consumer
from fedasync.commons.utils.producer import Producer
import logging
from fedasync.commons.conf import Config, RoutingRules
from fedasync.server.dependencies_container import DependenciesContainer
from fedasync.server.objects import Worker
import threading

lock = threading.Lock()

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class ServerConsumer(Consumer):
    def __init__(self, dependencies: DependenciesContainer):
        super().__init__()
        self.dependencies = dependencies

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
            response.session_id = client_init_message.sessionid
            response.client_id = new_worker.id
            # generate minio keys
            with lock:
                access_key, secret_key = self.dependencies.cloud_storage.generate_keys()

            response.access_key = access_key
            response.secret_key = secret_key

            LOGGER.info(f"server response: {response.__str__()} at {threading.current_thread()}")

            self._channel.basic_publish(
                Config.TRAINING_EXCHANGE,
                routing_key=RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT,
                body=response.serialize()
            )

            #  add to worker.
            with lock:
                self.dependencies.worker_manager.add_worker(new_worker)
                number_of_online_workers = self.dependencies.worker_manager.total()

            if number_of_online_workers > 1:
                # construct message.
                msg = ServerNotifyModelToClient()
                msg.model_id = self.dependencies.server.strategy.model_id
                msg.chosen_id = []
                msg.global_model_link = f"global_model_{self.dependencies.server.strategy.current_version}"
                msg.global_model_version = msg.model_id
                msg.avg_loss = self.dependencies.server.strategy.avg_loss
                msg.timestamp = 0
                msg.global_model_update_data_size = self.dependencies.server.strategy.global_model_update_data_size

                self._channel.basic_publish(
                    Config.TRAINING_EXCHANGE,
                    RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT,
                    msg.serialize()
                )

        elif method.routing_key == RoutingRules.CLIENT_NOTIFY_MODEL_TO_SERVER:
            # download local model.
            client_noty_message = ClientNotifyModelToServer(body.decode())

            # download model!
            with lock:
                # self.container.cloud_storage.download(f'{client_noty_message.client_id}/{client_noty_message.link}')
                self.dependencies.worker_manager.add_local_update(client_noty_message)

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


class ServerProducer(Producer):
    def __init__(self):
        super().__init__()

    def notify_global_model_to_client(self, message):
        self.publish_message(
            RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT,
            message
        )

    def response_to_client_init_connect(self, message):
        self.publish_message(
            RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT,
            message
        )
