import os, sys
import re
root = os.path.dirname(os.path.dirname(os.getcwd()))
sys.path.append(root)

import json
import logging
import threading
import uuid
from time import sleep

from asynfed.commons import Config
from asynfed.commons.conf import RoutingRules, init_config
from asynfed.commons.messages import ServerNotifyModelToClient, ClientNotifyModelToServer, ClientInit, \
    ServerInitResponseToClient
from asynfed.commons.messages.error_message import ErrorMessage
from asynfed.commons.messages.message_v2 import MessageV2
from asynfed.commons.utils.queue_consumer import AmqpConsumer
from asynfed.commons.utils.queue_producer import AmqpProducer
from asynfed.commons.utils.time_ultils import time_diff, time_now
from asynfed.server import Strategy, WorkerManager, ServerStorage
from asynfed.server.objects import Worker
from asynfed.server.strategies import AsynFL
from asynfed.server.messages import response_connection


lock = threading.Lock()

LOGGER = logging.getLogger(__name__)

class Server(object):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """

    def __init__(self, strategy: Strategy, config, t: int = 15, istest=True) -> None:
        # Server variables
        super().__init__()

        # config structure
        # {
        #     "server_id": "",
        #     "bucket_name": ""
        #     "queue_consumer": {
        #             'exchange_name': 'asynfl_exchange',
        #             'exchange_type': 'topic',
        #             'routing_key': 'server.#',
        #             'end_point': ''},
        #     "queue_producer": {
        #              'exchange_name': 'asynfl_exchange',
        #             'exchange_type': 'topic',
        #             'routing_key': 'client.#',
        #             'end_point': ""}
        # }

        self.config = config
        self._t = t
        self._strategy = strategy
        # variables
        self._is_downloading = False
        self._is_new_global_model = False

        # Record arive time for calculate dynamic waiting time for server.
        self._start_time = None
        self._first_arrival = None
        self._latest_arrival = None

        if istest:
            self._server_id = self.config['server_id']
        else:
            self._server_id = f'server-{str(uuid.uuid4())}'

        # All this information was decided by server to prevent conflict
        # because multiple server can use the same RabbitMQ, S3 server.
        Config.TRAINING_EXCHANGE = self._server_id

        if self.config['bucket_name'] is not None or self.config['bucket_name'] != "":
            Config.STORAGE_BUCKET_NAME = self.config['bucket_name']
        else:
            Config.STORAGE_BUCKET_NAME = self._server_id
        Config.STORAGE_BUCKET_NAME = "hellothisisnewbucket2"
        #
        init_config("server")

        LOGGER.info(f'\n\nServer Info:\n\tQueue In : {self.config["queue_consumer"]}'
                    f'\n\tQueue Out : {self.config["queue_producer"]}'
                    f'\n\tS3 Bucket: {Config.STORAGE_BUCKET_NAME}'
                    f'\n\n')

        # Initialize dependencies
        self._worker_manager: WorkerManager = WorkerManager()
        self._cloud_storage: ServerStorage = ServerStorage(self)
        #
        # self.delete_bucket_on_exit = True
        #
        self.thread_consumer = threading.Thread(target=self._start_consumer, name="fedasync_server_consuming_thread")
        self.queue_concumer = AmqpConsumer(self.config['queue_consumer'], self)
        self.queue_producer = AmqpProducer(self.config['queue_producer'])
        print('Queue ready!')

    def __notify_global_model_to_client(self, message):
        # Send notify message to client.
        self.queue_producer.send_message(
                {"type": Config.SERVER_NOTIFY_MESSAGE,
                 "content": message.serialize()}
        )

        # Get the starting time of the epoch and reset vars
        self._start_time = time_now()
        self._first_arrival = None
        self._latest_arrival = None

    def __notify_error_to_client(self, message):
        # Send notify message to client.
        pass

    def __response_to_client_init_connect(self, message):
        # Send response message to client.
        self.queue_producer.send_message({
            "type": Config.SERVER_INIT_RESPONSE,
            "content": message.serialize()})

    def _start_consumer(self):
        self.queue_concumer.start()

    def start(self):

        # run the consuming thread!.
        self.thread_consumer.start()
        #
        # while not self.__is_stop_condition():
        #     #
        #     # if not thread.is_alive():
        #     #     if self.delete_bucket_on_exit:
        #     #         self._cloud_storage.delete_bucket()
        #     #     self.stop()
        #
        #     with lock:
        #         n_local_updates = len(self._worker_manager.get_completed_workers())
        #     if n_local_updates == 0:
        #         print(f'No local update found, sleep for {self._t} seconds...')
        #         # Sleep for t seconds.
        #         sleep(self._t)
        #     # elif n_local_updates == 1:
        #     #     print("Hello")
        #     elif n_local_updates > 0:
        #         try:
        #             print(f'Found {n_local_updates} local update(s)')
        #             print('Start update global model')
        #             # calculate self._strategy.avg_qod and self._strategy.avg_loss
        #             # and self_strategy.global_model_update_data_size
        #             # within the self.__update function
        #             # self.__update()
        #             self.__update(n_local_updates)
        #             # Clear worker queue after aggregation.
        #             # self._worker_manager.update_worker_after_training()
        #             self.__publish_global_model()
        #
        #
        #         except Exception as e:
        #             message = ErrorMessage(str(e), None)
        #             LOGGER.info("*" * 20)
        #             LOGGER.info(e)
        #             LOGGER.info("THIS IS THE INTENDED MESSAGE")
        #             LOGGER.info("*" * 20)
        #             self.__notify_error_to_client(message)
        #
        # self.stop()
        # # thread.join()
        #
    def on_message_received(self, ch, method, props, body):
        msg_received = MessageV2.serialize(body.decode('utf-8'))
        if msg_received['message_type'] == Config.CLIENT_INIT_MESSAGE:
            self._response_connection(msg_received)
            return
            try:
                # # Get message from Client
                # client_init_message: ClientInit = ClientInit()
                # client_init_message.deserialize(receive_msg['content'])
                # LOGGER.info(f"client_msg: {client_init_message.__str__()} at {threading.current_thread()}")

                # check if session is in the worker_manager.get_all_worker_session
                if client_init_message.session_id in self._worker_manager.list_all_worker_session_id() and client_init_message.client_id != '':

                    # get worker_id by client_id
                    worker = self._worker_manager.get_worker_by_id(client_init_message.client_id)
                    worker_id = worker.worker_id
                    session_id = client_init_message.session_id

                elif client_init_message.client_id != '' or client_init_message.client_id != None:
                    worker_id = client_init_message.client_id
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
                error_message = ErrorMessage(error_message=e.__str__(), client_id=receive_msg['content']['client_id'])
                self.__notify_error_to_client(error_message)

        elif receive_msg['type'] == Config.CLIENT_NOTIFY_MESSAGE:
            client_notify_message = ClientNotifyModelToServer()
            client_notify_message.deserialize(receive_msg['content'])

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

    def _response_connection(self, msg_received):
        client_id = msg_received['headers']['client_id']
        session_id = msg_received['headers']['session_id']
        content = msg_received['content']
        with lock:
            access_key, secret_key = self._cloud_storage.get_client_key(client_id)
        worker = Worker(
            session_id=session_id,
            worker_id=client_id,
            sys_info=content['system_info'],
            data_size=content['data_description']['data_size'],
            qod=content['data_description']['qod'],
        )
        with lock:
            worker.access_key_id = access_key
            worker.secret_key_id = secret_key
            self._worker_manager.add_worker(worker)


        try:
            model_name = self._cloud_storage.get_newest_global_model().split('.')[0]
            model_version = model_name.split('_')[1][1:]

        except Exception as e:
            model_version = -1

        try:
            self._strategy.current_version = int(model_version)
        except Exception as e:
            logging.error(e)
            self._strategy.current_version = 0

        model_url = self._cloud_storage.get_newest_global_model()

        model_info = {
            "model_url": model_url,
            "global_model_name": model_url.split("/")[1],
            # use regex to get model version base on the global_model_name, e.g. "model_v1" -> "1"
            "model_version": re.findall(r'\d+', model_url.split("/")[1])[0]
        }
        aws_info = {
            "access_key": access_key,
            "secret_key": secret_key,
            "bucket_name": Config.STORAGE_BUCKET_NAME,
            "region_name": Config.STORAGE_REGION_NAME,
        }
        queue_info = {
            "training_exchange": "",
            "monitor_queue": "",
        }
        content = response_connection.ResponseConnection(model_info, aws_info, queue_info, reconnect=False)
        message = MessageV2(Config.SERVER_INIT_RESPONSE, content).to_json()
        self.queue_producer.send_data(message)


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


if __name__ == '__main__':
    import dotenv
    dotenv.load_dotenv()

    conf = {
        "server_id": "test_server_id",
        "bucket_name": "test_bucket",
        "queue_consumer": {
            'exchange_name': 'asynfl_exchange',
            'exchange_type': 'topic',
            'queue_name': 'server_consumer',
            'routing_key': 'server.#',
            'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu'
        },
        "queue_producer": {
            'exchange_name': 'asynfl_exchange',
            'exchange_type': 'topic',
            'queue_name': 'server_queue',
            'routing_key': 'client.#',
            'end_point': "amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu"
        }
    }
    Config.STORAGE_ACCESS_KEY = os.getenv("access_key")
    Config.STORAGE_SECRET_KEY = os.getenv("secret_key")

    strat = AsynFL()
    server = Server(strat, conf)
    server.start()
