import logging
import uuid
from time import sleep
from pika import BasicProperties
from asynfed.commons.conf import RoutingRules, Config, init_config
from asynfed.commons.messages.client_init_connect_to_server import ClientInit
from asynfed.commons.messages.client_notify_model_to_server import ClientNotifyModelToServer
from asynfed.commons.messages.server_init_response_to_client import ServerInitResponseToClient
from asynfed.commons.messages.server_notify_model_to_client import ServerNotifyModelToClient
from asynfed.commons.utils.queue_connector import QueueConnector
from asynfed.commons.utils.time_ultils import time_diff, time_now
from .objects import Worker
from .server_storage_connector import ServerStorage
from .strategies import Strategy
from .worker_manager import WorkerManager
import threading

from ..commons.messages.error_message import ErrorMessage
from ..commons.utils.queue_connector_blocking import BlockingQueueConnector

# from pynput import keyboard

lock = threading.Lock()

LOGGER = logging.getLogger(__name__)


class Server(QueueConnector):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """

    def __init__(self, strategy: Strategy, t: int = 15, test=True,
                 training_exchange: str = "test-client-tensorflow-cifar10",
                 bucket_name='test-client-tensorflow-cifar10') -> None:
        # Server variables
        super().__init__()
        self._t = t
        self._strategy = strategy
        # variables
        self._is_downloading = False
        self._is_new_global_model = False

        # Record arive time for calculate dynamic waiting time for server.
        self._start_time = None
        self._first_arrival = None
        self._latest_arrival = None

        if test:
            self._server_id = training_exchange
        else:
            self._server_id = f'server-{str(uuid.uuid4())}'

        # All this information was decided by server to prevent conflict
        # because multiple server can use the same RabbitMQ, S3 server.
        Config.TRAINING_EXCHANGE = self._server_id

        if test:
            Config.STORAGE_BUCKET_NAME = bucket_name
            Config.QUEUE_NAME = bucket_name
        else:
            Config.STORAGE_BUCKET_NAME = self._server_id
            Config.QUEUE_NAME = self._server_id

        init_config("server")

        LOGGER.info(f' \n\nServer Info:\n\tRabbitMQ Exchange : {Config.TRAINING_EXCHANGE}'
                    f'\n\tS3 Bucket: {Config.STORAGE_BUCKET_NAME}'
                    f'\n\n')

        # Initialize dependencies
        self._worker_manager: WorkerManager = WorkerManager()
        self._cloud_storage: ServerStorage = ServerStorage()

        self.delete_bucket_on_exit = True

    def on_message(self, channel, method, properties: BasicProperties, body):

        if method.routing_key == RoutingRules.CLIENT_INIT_SEND_TO_SERVER:
            try:
                # Get message from Client
                client_init_message: ClientInit = ClientInit()
                client_init_message.deserialize(body.decode())
                LOGGER.info(f"client_msg: {client_init_message.__str__()} at {threading.current_thread()}")

                # check if session is in the worker_manager.get_all_worker_session
                if client_init_message.session_id in self._worker_manager.list_all_worker_session_id() and client_init_message.client_id != '':

                    # get worker_id by client_id
                    worker = self._worker_manager.get_worker_by_id(client_init_message.client_id)
                    worker_id = worker.worker_id
                    session_id = client_init_message.session_id

                else:
                    worker_id = str(uuid.uuid4())
                    session_id = str(uuid.uuid4())

                    # Get cloud storage keys
                    with lock:
                        access_key, secret_key = self._cloud_storage.get_client_key(worker_id)

                    # Add worker to Worker Manager.
                    worker = Worker(
                        session_id=session_id,
                        worker_id=worker_id,
                        sys_info=client_init_message.sys_info,
                        data_size=client_init_message.data_size,
                        qod=client_init_message.qod
                    )
                    with lock:
                        worker.access_key_id = access_key
                        worker.secret_key_id = secret_key
                        self._worker_manager.add_worker(worker)

                model_name = self._cloud_storage.get_newest_global_model().split('.')[0]
                try:
                    model_version = model_name.split('_')[1][1:]

                except Exception as e:
                    model_version = -1
                try:
                    self._strategy.current_version = int(model_version)
                except Exception as e:
                    logging.error(e)
                    self._strategy.current_version = 0

                model_url = self._cloud_storage.get_newest_global_model()
                # Build response message
                response = ServerInitResponseToClient(
                    client_identifier=client_init_message.client_identifier,
                    session_id=session_id,
                    client_id=worker_id,
                    model_url=model_url,
                    global_model_name=model_url.split("/")[1],
                    model_version=self._strategy.current_version,
                    access_key=worker.access_key_id,
                    secret_key=worker.secret_key_id,
                    bucket_name=Config.STORAGE_BUCKET_NAME,
                    region_name=Config.STORAGE_REGION_NAME,
                    training_exchange=Config.TRAINING_EXCHANGE,
                    monitor_queue=Config.MONITOR_QUEUE

                )
                LOGGER.info(f"server response: {response.__str__()} at {threading.current_thread()}")
                self.__response_to_client_init_connect(response)

            except Exception as e:
                error_message = ErrorMessage(error_message=e.__str__(), client_id=body.decode["client_id"])
                self.__notify_error_to_client(error_message)

        elif method.routing_key == RoutingRules.CLIENT_NOTIFY_MODEL_TO_SERVER:
            client_notify_message = ClientNotifyModelToServer()
            client_notify_message.deserialize(body.decode())

            if self._strategy.current_version == client_notify_message.global_model_version_used:
                if self._first_arrival is None:
                    self._first_arrival = time_now()
                    self._latest_arrival = time_now()

                elif self._first_arrival is not None:
                    self._latest_arrival = time_now()

            # Download model!
            with lock:
                self._cloud_storage.download(remote_file_path=client_notify_message.weight_file,
                                             local_file_path=Config.TMP_LOCAL_MODEL_FOLDER + client_notify_message.model_id)
                self._worker_manager.add_local_update(client_notify_message)

            print("*" * 20)
            print(f'Receive new model from client [{client_notify_message.client_id}]!')
            print(self._worker_manager.worker_pool[client_notify_message.client_id].data_size)
            print(self._worker_manager.worker_pool[client_notify_message.client_id].is_completed)
            print(f'Performance and Loss: {client_notify_message.performance}, {client_notify_message.loss_value}')
            print("*" * 20)




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

        self._channel.queue_purge(Config.QUEUE_NAME)

        self.start_consuming()

    def __notify_global_model_to_client(self, message):
        # Send notify message to client.
        self._channel.basic_publish(
            Config.TRAINING_EXCHANGE,
            RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT,
            message.serialize()
        )
        # Get the starting time of the epoch and reset vars
        self._start_time = time_now()
        self._first_arrival = None
        self._latest_arrival = None

    def __notify_error_to_client(self, message):
        # Send notify message to client.
        self._channel.basic_publish(
            Config.TRAINING_EXCHANGE,
            RoutingRules.SERVER_ERROR_TO_CLIENT,
            message.serialize()
        )

    def __response_to_client_init_connect(self, message):
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

        # thread = threading.Thread(target=keyboard_thread)
        # thread.start()

        while not self.__is_stop_condition() and not self._closing:
            #
            # if not thread.is_alive():
            #     if self.delete_bucket_on_exit:
            #         self._cloud_storage.delete_bucket()
            #     self.stop()

            with lock:
                n_local_updates = len(self._worker_manager.get_completed_workers())
            if n_local_updates == 0:
                print(f'No local update found, sleep for {self._t} seconds...')
                # Sleep for t seconds.
                sleep(self._t)
            # elif n_local_updates == 1:
            #     print("Hello")
            elif n_local_updates > 0:
                try:
                    print(f'Found {n_local_updates} local update(s)')
                    print('Start update global model')
                    # calculate self._strategy.avg_qod and self._strategy.avg_loss 
                    # and self_strategy.global_model_update_data_size
                    # within the self.__update function
                    # self.__update()
                    self.__update(n_local_updates)
                    # Clear worker queue after aggregation.
                    # self._worker_manager.update_worker_after_training()
                    self.__publish_global_model()


                except Exception as e:
                    message = ErrorMessage(str(e), None)
                    LOGGER.info("*" * 20)
                    LOGGER.info(e)
                    LOGGER.info("THIS IS THE INTENDED MESSAGE")
                    LOGGER.info("*" * 20)
                    self.__notify_error_to_client(message)

        self.stop()
        # thread.join()

    # def

    def __update(self, n_local_updates):
        if n_local_updates == 1:
            self._strategy.current_version += 1
            print("Only one update from client, passing the model to all other client in the network...")
            completed_workers: dict[str, Worker] = self._worker_manager.get_completed_workers()

            # get the only worker
            # worker = next(iter(completed_workers.values))
            for w_id, worker in completed_workers.items():
                print(w_id)
                self._strategy.avg_loss = worker.loss
                self._strategy.avg_qod = worker.qod
                self._strategy.global_model_update_data_size = worker.data_size
                worker.is_completed = False

            # print("*" * 10)
            # print(f"Avg loss, avg qod, global datasize: {self._strategy.avg_loss}, {self._strategy.avg_qod}, {self._strategy.global_model_update_data_size}")
            # print("*" * 10)

            # copy the worker model weight to the global model folder
            import shutil
            local_weight_file = worker.get_weight_file_path()
            save_location = Config.TMP_GLOBAL_MODEL_FOLDER + self._strategy.get_global_model_filename()
            shutil.copy(local_weight_file, save_location)


        else:
            print("Aggregating process...")
            # calculate self._strategy.avg_qod and self_strategy.avg_loss
            # and self_strategy.global_model_update_data_size
            # within the self._strategy.aggregate function
            self._strategy.aggregate(self._worker_manager)

        # calculate dynamic time ratial only when 
        if None not in [self._start_time, self._first_arrival, self._latest_arrival]:
            t1 = time_diff(self._start_time, self._first_arrival)
            t2 = time_diff(self._start_time, self._latest_arrival)

            # get avg complete time of current epoch
            self._t = (t2 + t1) / 2 + 2 * t1

    def __is_stop_condition(self):
        self._strategy.is_completed()

    def __publish_global_model(self):
        print('Publish global model (sv notify model to client)')
        local_filename = f'{Config.TMP_GLOBAL_MODEL_FOLDER}{self._strategy.model_id}_v{self._strategy.current_version}.pkl'
        remote_filename = f'global-models/{self._strategy.model_id}_v{self._strategy.current_version}.pkl'
        self._cloud_storage.upload(local_filename, remote_filename)

        # Construct message
        msg = ServerNotifyModelToClient(
            chosen_id=[],
            model_id=self._strategy.model_id,

            global_model_version=self._strategy.current_version,
            global_model_name=f'{self._strategy.model_id}_v{self._strategy.current_version}.pkl',
            # values obtained after each update time
            global_model_update_data_size=self._strategy.global_model_update_data_size,
            avg_loss=self._strategy.avg_loss,
            avg_qod=self._strategy.avg_qod,
        )
        print("*" * 20)
        print("Notify model from server")
        print(msg)
        print("*" * 20)
        # Send message
        self.__notify_global_model_to_client(msg)

#
# def on_press(key):
#     if key == keyboard.Key.esc:
#         return False
#
#
# def keyboard_thread():
#     # Create a listener instance
#     listener = keyboard.Listener(on_press=on_press)
#
#     # Start the listener
#     listener.start()
#
#     # Wait for the listener to finish (blocking operation)
#     listener.join()
