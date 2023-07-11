from datetime import datetime
import os, sys
import re

from asynfed.server.messages.ping_to_client import PingToClient


root = os.path.dirname(os.path.dirname(os.getcwd()))
sys.path.append(root)

from asynfed.server.messages.notify_new_model import NotifyNewModel
import logging
import threading
import uuid
from time import sleep

from asynfed.commons import Config
from asynfed.commons.conf import init_config

from asynfed.commons.messages import MessageV2
from asynfed.commons.utils import AmqpConsumer
from asynfed.commons.utils import AmqpProducer
from asynfed.commons.utils import  time_now


from .strategies import Strategy
from .objects import Worker
from .server_storage_connector import ServerStorageAWS
from .influxdb import InfluxDB
from .worker_manager import WorkerManager


from asynfed.server.messages import ResponseConnection
from asynfed.server.messages import StopTraining

import concurrent.futures
thread_pool_ref = concurrent.futures.ThreadPoolExecutor


lock = threading.Lock()

LOGGER = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
LOGGER.setLevel(logging.INFO)

class Server(object):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """

    def __init__(self, strategy: Strategy, config: dict, save_log=False) -> None:
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
            "stop_conditions": {
                "max_version": 50,
                "max_performance": 0.9,
                "min_loss": 0.1
            },
            "model_exchange_at":{
                    "performance": 85,
                    "epoch": 100
            }
        }
        """
        super().__init__()

        if config.get('stop_conditions'):
            self.stop_conditions = config.get('stop_conditions')
        else:
            self.stop_conditions = {
                'max_version': 300,
                'max_performance': 0.95,
                'min_loss': 0.01
            }
        if config.get('model_exchange_at'):
            self.model_exchange_at = config.get("model_exchange_at")
        else:
            self.model_exchange_at = {
                "performance": 85,
                "epoch": 100}

        self.weights_trained = {}
        self._is_stop_condition = False

        self.config = config
        self._t = config.get('t') or 15
        self.ping_time = config.get('ping_time') or 300
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

        if config.get('aws').get('bucket_name') is None or self.config.get('aws').get('bucket_name') == "":
            config['aws']['bucket_name'] = self._server_id
        
        init_config("server", save_log)

        LOGGER.info(f'\n\nServer Info:\n\tQueue In : {self.config["queue_consumer"]}'
                    f'\n\tQueue Out : {self.config["queue_producer"]}'
                    f'\n\tS3 Bucket: {self.config["aws"]["bucket_name"]}'
                    f'\n\n')

        # Initialize dependencies
        self._worker_manager: WorkerManager = WorkerManager()
        self._cloud_storage: ServerStorageAWS = ServerStorageAWS(config['aws'])
        self._influxdb = InfluxDB(config['influxdb'])

        self.thread_consumer = threading.Thread(target=self._start_consumer, name="fedasync_server_consuming_thread")
        self.thread_consumer.daemon = True
        self.queue_consumer = AmqpConsumer(self.config['queue_consumer'], self)
        self.queue_producer = AmqpProducer(self.config['queue_producer'])

        self.ping_thread = threading.Thread(target=self._ping, name="fedasync_server_ping_thread")
        self.ping_thread.daemon = True

        LOGGER.info('Queue ready!')


    def _start_consumer(self):
        self.queue_consumer.start()

    def _start_ping(self):
        self.ping_thread.start()

    def _ping(self):
        while True:
            for client_id in self._worker_manager.list_connected_workers():
                LOGGER.info(f'Ping to client {client_id}')
                content = PingToClient(client_id)
                message = MessageV2(
                        headers={'timestamp': time_now(), 'message_type': Config.SERVER_PING_TO_CLIENT, 'server_id': self._server_id},
                        content=content
                ).to_json()
                self.queue_producer.send_data(message)
            sleep(self.ping_time)

    def start(self):
        self.thread_consumer.start()
        self._start_ping()
        while True:
            if self._is_stop_condition:
                LOGGER.info('Stop condition is reached!')
                break
            # if self.__is_stop_condition({"version": self._strategy.current_version}):
            #     content = StopTraining()
            #     message = MessageV2(
            #             headers={'timestamp': time_now(), 'message_type': Config.SERVER_STOP_TRAINING, 'server_id': self._server_id},
            #             content=content
            #             ).to_json()
            #     self.queue_producer.send_data(message)

            #     best_weight = None  
            #     best_acc = 0
            #     for k, v in self.weights_trained.items():
            #         if v['performance'] > best_acc:
            #             best_acc = v['performance']
            #             best_weight = k
            #     LOGGER.info(f'Best weight: {best_weight} - acc: {best_acc} -- loss: {self.weights_trained[best_weight]["loss"]}')
            #     break

            with lock:
                n_local_updates = len(self._worker_manager.get_completed_workers())
            if n_local_updates == 0:
                LOGGER.info(f'No local update found, sleep for {self._t} seconds...')
                sleep(self._t)
            elif n_local_updates > 0:
                try:
                    LOGGER.info(f'Start update global model with {n_local_updates} local updates')
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

    def on_message_received(self, ch, method, props, body):
        msg_received = MessageV2.deserialize(body.decode('utf-8'))
        msg_type = msg_received['headers']['message_type']

        if msg_type == Config.CLIENT_INIT_MESSAGE:
            self._response_connection(msg_received)
        elif msg_type == Config.CLIENT_NOTIFY_MESSAGE:
            self._handle_client_notify_model(msg_received)
        elif msg_type == Config.CLIENT_NOTIFY_EVALUATION:
            self._handle_client_notify_evaluation(msg_received)
        elif msg_type == Config.CLIENT_PING_MESSAGE:
            MessageV2.print_message(msg_received)
            self._worker_manager.update_worker_last_ping(msg_received['headers']['client_id'])


    def _response_connection(self, msg_received):
        MessageV2.print_message(msg_received)
        client_id = msg_received['headers']['client_id']
        session_id = str(uuid.uuid4())
        content = msg_received['content']


        if msg_received['headers']['session_id'] in self._worker_manager.list_sessions():
            reconnect = True
            worker = self._worker_manager.get_worker_by_id(client_id)
            access_key, secret_key = worker.access_key_id, worker.secret_key_id
        else:
            reconnect = False
            worker = Worker(
                    session_id=session_id,
                    worker_id=client_id,
                    sys_info=content['system_info'],
                    data_size=content['data_description']['data_size'],
                    qod=content['data_description']['qod'],
            )
            LOGGER.info("*" * 20)
            LOGGER.info(worker)
            LOGGER.info("*" * 20)
            access_key, secret_key = self._cloud_storage.get_client_key(client_id)
            worker.access_key_id = access_key
            worker.secret_key_id = secret_key
            self._worker_manager.add_worker(worker)

            folder_name = f'{Config.TMP_LOCAL_MODEL_FOLDER}{worker.worker_id}'
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)

        try:
            model_name = self._cloud_storage.get_newest_global_model().split('.')[0]
            model_version = model_name.split('_')[1][1:]

        except Exception as e:
            model_version = -1

        try:
            self._strategy.current_version = int(model_version)
        except Exception as e:
            logging.error(e)
            self._strategy.current_version = 1

        model_url = self._cloud_storage.get_newest_global_model()
        model_info = {"model_url": model_url, 
                      "global_model_name": model_url.split("/")[-1], 
                      "model_version": int(re.findall(r'\d+', model_url.split("/")[1])[0]),
                      "exchange_at": self.model_exchange_at
                    }
        aws_info = {"access_key": access_key, 
                    "secret_key": secret_key, 
                    "bucket_name": self.config['aws']['bucket_name'],
                    "region_name": self.config['aws']['region_name'],
                    "parent": None}
        queue_info = {"training_exchange": "", 
                      "monitor_queue": ""}

        message = MessageV2(
                headers={'timestamp': time_now(), 'message_type': Config.SERVER_INIT_RESPONSE, 'server_id': self._server_id}, 
                content=ResponseConnection(session_id, model_info, aws_info, queue_info, reconnect=reconnect)
        ).to_json()
        self.queue_producer.send_data(message)

    def _handle_client_notify_model(self, msg_received):
        MessageV2.print_message(msg_received)
        client_id = msg_received['headers']['client_id']

        # self._cloud_storage.download(remote_file_path=msg_received['content']['remote_worker_weight_path'],
        #                                 local_file_path=Config.TMP_LOCAL_MODEL_FOLDER + msg_received['content']['filename'])
        self._worker_manager.add_local_update(client_id, msg_received['content'])
        self._influxdb.write_training_process_data(msg_received)

    def _handle_client_notify_evaluation(self, msg_received):
        MessageV2.print_message(msg_received)
        self.weights_trained[msg_received['content']['weight_file']] = {'loss': msg_received['content']['loss'], 'performance': msg_received['content']['performance']}
        if self.__is_stop_condition(msg_received['content']):
            content = StopTraining()
            message = MessageV2(
                    headers={'timestamp': time_now(), 'message_type': Config.SERVER_STOP_TRAINING, 'server_id': self._server_id},
                    content=content
            ).to_json()
            self.queue_producer.send_data(message)

            best_weight = None  
            best_acc = 0
            for k, v in self.weights_trained.items():
                if v['performance'] > best_acc:
                    best_acc = v['performance']
                    best_weight = k

            LOGGER.info(f'Best weight: {best_weight} - acc: {best_acc} -- loss: {self.weights_trained[best_weight]["loss"]}')

            self._is_stop_condition = True
            sys.exit(0)


    def __update(self, n_local_updates):
        if n_local_updates == 1:
            self._strategy.current_version += 1
            LOGGER.info("Only one update from client, passing the model to all other client in the network...")
            completed_workers: dict[str, Worker] = self._worker_manager.get_completed_workers()

            # get the only worker
            # worker = next(iter(completed_workers.values))
            for w_id, worker in completed_workers.items():
                LOGGER.info(w_id)
                self._strategy.avg_loss = worker.loss
                self._strategy.avg_qod = worker.qod
                self._strategy.global_model_update_data_size = worker.data_size
                worker.is_completed = False

                # print("*" * 20)
                # print("remote file path: ", worker.get_remote_weight_file_path())
                # print("save file path: ", worker.get_remote_weight_file_path())
                # print("*" * 20)

                remote_weight_file = worker.get_remote_weight_file_path()
                local_weight_file = worker.get_weight_file_path()
                self._cloud_storage.download(remote_file_path= remote_weight_file, 
                                             local_file_path= local_weight_file)
            # print("*" * 10)
            # print(f"Avg loss, avg qod, global datasize: {self._strategy.avg_loss}, {self._strategy.avg_qod}, {self._strategy.global_model_update_data_size}")
            # print("*" * 10)

            # copy the worker model weight to the global model folder
            import shutil
            # local_weight_file = worker.get_weight_file_path()
            save_location = Config.TMP_GLOBAL_MODEL_FOLDER + self._strategy.get_global_model_filename()
            shutil.copy(local_weight_file, save_location)


        else:
            LOGGER.info("Aggregating process...")
            # calculate self._strategy.avg_qod and self_strategy.avg_loss
            # and self_strategy.global_model_update_data_size
            # within the self._strategy.aggregate function
            self._strategy.aggregate(self._worker_manager, self._cloud_storage)

        # # calculate dynamic time ratial only when
        # if None not in [self._start_time, self._first_arrival, self._latest_arrival]:
        #     t1 = time_diff(self._start_time, self._first_arrival)
        #     t2 = time_diff(self._start_time, self._latest_arrival)

        #     # get avg complete time of current epoch
        #     self._t = (t2 + t1) / 2 
        #     # self._t = (t2 + t1) / 2 + 2 * t1

    def __is_stop_condition(self, info):
        for k, v in info.items():
            if k == "loss" and self.stop_conditions.get("min_loss") is not None:
                if v <= self.stop_conditions.get("min_loss"):
                    LOGGER.info(f"Stop condition: loss {v} <= {self.stop_conditions.get('min_loss')}")
                    return True
            elif k == "performance" and self.stop_conditions.get("max_performance") is not None:
                if v >= self.stop_conditions.get("max_performance"):
                    LOGGER.info(f"Stop condition: performance {v} >= {self.stop_conditions.get('max_performance')}")
                    return True
            # elif k == "version" and self.stop_conditions.get("max_version") is not None:
            #     if v >= self.stop_conditions.get("max_version"):
            #         LOGGER.info(f"Stop condition: version {v} >= {self.stop_conditions.get('max_version')}")
            #         return True
            elif k == "weight_file" and self.stop_conditions.get("max_version") is not None:
                version = int(v.split("_")[-1][1])
                if version >= self.stop_conditions.get("max_version"):
                    LOGGER.info(f"Stop condition: version {version} >= {self.stop_conditions.get('max_version')}")
                    return True

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
