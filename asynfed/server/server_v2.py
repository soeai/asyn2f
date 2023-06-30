import os, sys
import re

root = os.path.dirname(os.path.dirname(os.getcwd()))
sys.path.append(root)

from asynfed.server.messages.notify_new_model import NotifyNewModel
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
import concurrent.futures
thread_pool_ref = concurrent.futures.ThreadPoolExecutor


lock = threading.Lock()

LOGGER = logging.getLogger(__name__)

class Server(object):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """

    def __init__(self, strategy: Strategy, config: dict) -> None:
        """
        config structure
        {
            "server_id": "",
            "bucket_name": "",
            "region_name": "ap-southeast-2",
            "t": 15,
            "queue_consumer": {
                'exchange_name': 'asynfl_exchange',
                'exchange_type': 'topic',
                'routing_key': 'server.#',
                'end_point': ''},
            "queue_producer": {
                'exchange_name': 'asynfl_exchange',
                'exchange_type': 'topic',
                'routing_key': 'client.#',
                'end_point': ""}
        }
        """
        super().__init__()

        self.config = config
        self._t = config.get('t') or 15
        self._strategy = strategy
        # variables
        self._is_downloading = False
        self._is_new_global_model = False

        # Record arive time for calculate dynamic waiting time for server.
        self._start_time = None
        self._first_arrival = None
        self._latest_arrival = None

        if config.get('test'):
            self._server_id = self.config['server_id']
        else:
            self._server_id = f'server-{str(uuid.uuid4())}'

        # All this information was decided by server to prevent conflict
        # because multiple server can use the same RabbitMQ, S3 server.

        if self.config['bucket_name'] is not None or self.config['bucket_name'] != "":
            Config.STORAGE_BUCKET_NAME = self.config['bucket_name']
        else:
            Config.STORAGE_BUCKET_NAME = self._server_id
        #
        init_config("server")

        LOGGER.info(f'\n\nServer Info:\n\tQueue In : {self.config["queue_consumer"]}'
                    f'\n\tQueue Out : {self.config["queue_producer"]}'
                    f'\n\tS3 Bucket: {Config.STORAGE_BUCKET_NAME}'
                    f'\n\n')

        # Initialize dependencies
        self._worker_manager: WorkerManager = WorkerManager()
        aws_config = {
            "access_key": Config.STORAGE_ACCESS_KEY,
            "secret_key": Config.STORAGE_SECRET_KEY,
            "region_name": Config.STORAGE_REGION_NAME,
            "bucket_name": Config.STORAGE_BUCKET_NAME,
            "parent": None
        }
        self._cloud_storage: ServerStorage = ServerStorage(aws_config)

        self.thread_consumer = threading.Thread(target=self._start_consumer, name="fedasync_server_consuming_thread")
        self.queue_concumer = AmqpConsumer(self.config['queue_consumer'], self)
        self.queue_producer = AmqpProducer(self.config['queue_producer'])
        print('Queue ready!')


    def __notify_error_to_client(self, message):
        # Send notify message to client.
        pass


    def _start_consumer(self):
        self.queue_concumer.start()

    def start(self):

        # run the consuming thread!.
        self.thread_consumer.start()
        #
        while not self.__is_stop_condition():

            with lock:
                n_local_updates = len(self._worker_manager.get_completed_workers())
            if n_local_updates == 0:
                print(f'No local update found, sleep for {self._t} seconds...')
                sleep(self._t)
            # elif n_local_updates == 1:
            #     print("Hello")
            elif n_local_updates > 0:
                try:
                    print(f'Start update global model with {n_local_updates} local updates')
                    # calculate self._strategy.avg_qod and self._strategy.avg_loss
                    # and self_strategy.global_model_update_data_size
                    # within the self.__update function
                    # self.__update()
                    self.__update(n_local_updates)
                    # Clear worker queue after aggregation.
                    # self._worker_manager.update_worker_after_training()
                    self._publish_global_model()


                except Exception as e:
                    raise e
                    # message = ErrorMessage(str(e), None)
                    # LOGGER.info("*" * 20)
                    # LOGGER.info(e)
                    # LOGGER.info("THIS IS THE INTENDED MESSAGE")
                    # LOGGER.info("*" * 20)
                    # self.__notify_error_to_client(message)

    def on_message_received(self, ch, method, props, body):
        msg_received = MessageV2.serialize(body.decode('utf-8'))
        if msg_received['headers']['message_type'] == Config.CLIENT_INIT_MESSAGE:
            self._response_connection(msg_received)
        elif msg_received['headers']['message_type'] == Config.CLIENT_NOTIFY_MESSAGE:
            self._handle_client_notify_message(msg_received)


    def _response_connection(self, msg_received):
        client_id = msg_received['headers']['client_id']
        session_id = str(uuid.uuid4())
        content = msg_received['content']

        if msg_received['session_id'] in self._worker_manager.list_all_worker_session_id:
            reconnect = True
        else:
            reconnect = False
            worker = Worker(
                    session_id=session_id,
                    worker_id=client_id,
                    sys_info=content['system_info'],
                    data_size=content['data_description']['data_size'],
                    qod=content['data_description']['qod'],
            )
            worker.access_key_id = access_key
            worker.secret_key_id = secret_key
            self._worker_manager.add_worker(worker)

        access_key, secret_key = self._cloud_storage.get_client_key(client_id)

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
        model_info = {"model_url": model_url, 
                      "global_model_name": model_url.split("/")[-1], 
                      "model_version": int(re.findall(r'\d+', model_url.split("/")[1])[0]) }
        aws_info = {"access_key": access_key, 
                    "secret_key": secret_key, 
                    "bucket_name": self.config['bucket_name'],
                    "region_name": self.config['region_name'],
                    "parent": None}
        queue_info = {"training_exchange": "", 
                      "monitor_queue": ""}

        message = MessageV2(
                headers={'timestamp': time_now(), 'message_type': Config.SERVER_INIT_RESPONSE, 'server_id': self._server_id}, 
                content=response_connection.ResponseConnection(session_id, model_info, aws_info, queue_info, reconnect=reconnect)
        ).to_json()
        self.queue_producer.send_data(message)

    def _handle_client_notify_message(self, msg_received):
        print(msg_received)
        client_id = msg_received['headers']['client_id']

        self._cloud_storage.download(remote_file_path=msg_received['content']['remote_worker_weight_path'],
                                        local_file_path=Config.TMP_LOCAL_MODEL_FOLDER + msg_received['content']['filename'])
        self._worker_manager.add_local_update(client_id, msg_received['content'])


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

    def _publish_global_model(self):
        local_filename = f'{Config.TMP_GLOBAL_MODEL_FOLDER}{self._strategy.model_id}_v{self._strategy.current_version}.pkl'
        remote_filename = f'global-models/{self._strategy.model_id}_v{self._strategy.current_version}.pkl'
        self._cloud_storage.upload(local_filename, remote_filename)

        message = MessageV2(
            headers={"timestamp": time_now(), "message_type": Config.SERVER_NOTIFY_MESSAGE, "server_id": self._server_id},
            content=NotifyNewModel(
                chosen_id=[],
                model_id=self._strategy.model_id,
                global_model_version=self._strategy.current_version,
                global_model_name=f'{self._strategy.model_id}_v{self._strategy.current_version}.pkl',
                global_model_update_data_size=self._strategy.global_model_update_data_size,
                avg_loss=self._strategy.avg_loss,
                avg_qod=self._strategy.avg_qod,
            )
        ).to_json()
        self.queue_producer.send_data(message)

        # Get the starting time of the epoch and reset vars
        self._start_time = time_now()
        self._first_arrival = None
        self._latest_arrival = None

