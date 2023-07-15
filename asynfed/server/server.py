
root = os.path.dirname(os.path.dirname(os.getcwd()))
sys.path.append(root)

import os
import sys
import json
import re
import logging
from threading import Thread, Lock
from time import sleep
import uuid
import copy
import concurrent.futures

from asynfed.commons import Config
from asynfed.commons.messages import MessageV2
from asynfed.commons.utils import AmqpConsumer, AmqpProducer
from asynfed.commons.conf import init_config as _logging_config
import asynfed.commons.utils.time_ultils as time_utils


from .server_aws_storage_connector import ServerStorageAWS
from .server_minio_storage_connector import ServerStorageMinio
from .influxdb import InfluxDB
from .strategies import Strategy
from .worker_manager import WorkerManager
from .objects import Worker, BestModel

from .messages import PingToClient, NotifyNewModel, ResponseConnection, StopTraining


thread_pool_ref = concurrent.futures.ThreadPoolExecutor
lock = Lock()

LOGGER = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
LOGGER.setLevel(logging.INFO)

class Server(object):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """
    def __init__(self, strategy: Strategy, config: dict) -> None:
        """
        config structure

        """
        super().__init__()
        # initialized some config for server
        _logging_config("server", save_log= config['save_log'])
        self._load_config(config= config)

        # boolean variable to check the exit condition
        self._is_stop_condition: bool = False
        # initialize an object to save best model info
        self._best_model: BestModel = BestModel()

        # Initialize dependencies
        self._strategy: Strategy = strategy
        self._cloud_storage = self._set_up_cloud_storage()
        self._worker_manager: WorkerManager = WorkerManager()
        self._influxdb: InfluxDB = InfluxDB(self._config['influxdb'])

        # queue
        self._queue_consumer: AmqpConsumer = AmqpConsumer(self._config['queue_consumer'], self)
        self._queue_producer: AmqpProducer = AmqpProducer(self._config['queue_producer'])

        self._consumer_thread = Thread(target=self._start_consumer, name="fedasync_server_consuming_thread")
        self._consumer_thread.daemon = True

        # ping thread
        self._ping_thread = Thread(target=self._ping, name="fedasync_server_ping_thread")
        self._ping_thread.daemon = True

        # clean cloud storage thread
        self._clean_cloud_storage_thread = Thread(target=self._clean_cloud_storage, name="fedasync_server_clean_cloud_storage_thread")
        self._clean_cloud_storage_thread.daemon = True

        LOGGER.info("-" * 40)
        LOGGER.info('Server config completed. Ready to listen!')
        LOGGER.info(f'\n\nServer Info:\n\tQueue In : {self._config["queue_consumer"]}'
                    f'\n\tQueue Out : {self._config["queue_producer"]}'
                    f'\n\tS3 Bucket: {self._bucket_name}'
                    f'\n\n')
        LOGGER.info("-" * 40)


    def start(self):
        self._consumer_thread.start()
        self._ping_thread.start()
        self._clean_cloud_storage_thread.start()
    
        while True:
            if self._is_stop_condition:
                LOGGER.info('Stop condition is reached!')
                # close the program
                sys.exit(0)


            with lock:
                n_local_updates = len(self._worker_manager.get_completed_workers())
            if n_local_updates == 0:
                LOGGER.info(f'No local update found, sleep for {self._update_period} seconds...')
                sleep(self._update_period)
            elif n_local_updates > 0:
                try:
                    LOGGER.info(f'Start update global model with {n_local_updates} local updates')
                    self._update(n_local_updates)
                    self._publish_global_model()

                except Exception as e:
                    raise e
                

    # function for queue consumer to call
    # handling when receiving message
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


    def _load_config(self, config):
        self._config = config

        # if the user do not set server_id
        # then generate it
        self._server_id: str = self._config.get('server_id') or f'server-{str(uuid.uuid4())}'

        self._stop_conditions: dict = self._config.get('stop_conditions', {'max_version': 300, 'max_performance': 0.95, 'min_loss': 0.01})
        self._model_exchange_at: dict = self._config.get('model_exchange_at', {"performance": 0.85, "epoch": 100})

        # time related
        # update_period is the waiting period between two aggregating process
        self._update_period: int = self._config.get('update_period') or 30
        self._ping_period: int = self._config.get('ping_period') or 300

        # cloud storage related
        self._cloud_storage_type: str = self._config['cloud_storage']['type']
        self._bucket_name: str = self._config['cloud_storage']['bucket_name']

        self._clean_cloud_storage_period: int = self._config.get('cloud_storage', {}).get('cleaning_config', {}).get('clean_cloud_storage_period', 300) 
        self._global_keep_version_num: int = self._config.get('cloud_storage', {}).get('cleaning_config', {}).get('global_keep_version_num', 5)
        self._local_keep_version_num: int = self._config.get('cloud_storage', {}).get('cleaning_config', {}).get('local_keep_version_num', 3)

    
    def _publish_global_model(self):
        # increment the current version to 1
        self._strategy.current_version += 1

        local_filename = f'{Config.TMP_GLOBAL_MODEL_FOLDER}{self._strategy.model_id}_v{self._strategy.current_version}.pkl'
        remote_filename = f'global-models/{self._strategy.model_id}_v{self._strategy.current_version}.pkl'

        self._cloud_storage.upload(local_filename, remote_filename)

        message = MessageV2(
            headers={"timestamp": time_utils.time_now(), "message_type": Config.SERVER_NOTIFY_MESSAGE, "server_id": self._server_id},
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
        self._queue_producer.send_data(message)


    def _set_up_cloud_storage(self):
        if self._cloud_storage_type == "aws_s3":
            cloud_storage: ServerStorageAWS = ServerStorageAWS(self._config['cloud_storage']['aws_s3'])
        elif self._cloud_storage_type == "minio":
            cloud_storage: ServerStorageMinio = ServerStorageMinio(self._config['cloud_storage']['minio'])
        else:
            LOGGER.info("There is no cloud storage")
            sys.exit(0)
        return cloud_storage


    def _start_consumer(self):
        self._queue_consumer.start()


    def _ping(self):
        while True:
            for client_id in self._worker_manager.list_connected_workers():
                LOGGER.info(f'Ping to client {client_id}')
                content = PingToClient(client_id)
                message = MessageV2(
                        headers={'timestamp': time_utils.time_now(), 'message_type': Config.SERVER_PING_TO_CLIENT, 'server_id': self._server_id},
                        content=content
                ).to_json()
                self._queue_producer.send_data(message)
            sleep(self._ping_period)

    def _clean_cloud_storage(self):
        while True:
            sleep(self._clean_cloud_storage_period)

            LOGGER.info("CLEANING TIME")
            # clean global folder first
            files = self._cloud_storage.list_files("global-models")
            current_version = self._strategy.current_version
            threshold = current_version - self._global_keep_version_num

            if self._best_model.model_name != "":
                best_model_name = self._best_model.model_name
                best_model_version = int(re.search(r"v(\d+)", best_model_name.split("_")[1]).group(1))
            else:
                best_model_version = None

            versions = [int(file.split("_")[-1].split(".")[0].split("v")[-1]) for file in files]
            delete_list = [file for file, version in zip(files, versions) if version <= threshold and version != best_model_version]

            if delete_list:
                LOGGER.info("=" * 20)
                LOGGER.info("Delete files in global-models folder")
                LOGGER.info(f"current global version: {current_version}, best model version: {best_model_version}, threshold: {threshold}, total deleted files: {len(delete_list)}")
                LOGGER.info(versions)
                LOGGER.info("=" * 20)
                self._cloud_storage.delete_files(delete_list)

            # clients folder
            workers = self._worker_manager.get_all_worker()
            for w_id, worker in workers.items():
                files = self._cloud_storage.list_files(parent_folder= "clients", target_folder= w_id)

                threshold = worker.update_local_version_used - self._local_keep_version_num

                delete_list = [file for file in files if int(file.split("_")[-1].split(".")[0].split("v")[-1]) <= threshold]
                if delete_list:
                    LOGGER.info("=" * 20)
                    LOGGER.info(f"worker id: {w_id}, current local update version used: {worker.update_local_version_used}, threshold: {threshold}, total deleted files: {len(delete_list)}")
                    LOGGER.info([int(file.split("_")[-1].split(".")[0].split("v")[-1]) for file in delete_list])
                    LOGGER.info("=" * 20)
                    self._cloud_storage.delete_files(delete_list)



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
            # new entry
            reconnect = False
            worker = Worker(
                    session_id=session_id,
                    worker_id=client_id,
                    sys_info=content['system_info'],
                    data_size=content['data_description']['data_size'],
                    qod=content['data_description']['qod'],
            )
            # create keys to cloud storage for worker
            access_key, secret_key = self._cloud_storage.get_client_key(client_id)
            worker.access_key_id = access_key
            worker.secret_key_id = secret_key

            # add to the worker manager 
            self._worker_manager.add_worker(worker)

            # create a local folder name to store weight file of worker
            folder_name = f'{Config.TMP_LOCAL_MODEL_FOLDER}{worker.worker_id}'
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)

        LOGGER.info("*" * 20)
        LOGGER.info(worker)
        LOGGER.info("*" * 20)

        # notify newest global model to worker
        model_url = self._cloud_storage.get_newest_global_model()
        global_model_name = model_url.split("/")[-1]
        model_version = int(re.search(r"v(\d+)", global_model_name.split("_")[1]).group(1))
        self._strategy.current_version = model_version

        model_info = {"model_url": model_url, 
                      "global_model_name": global_model_name, 
                      "model_version": model_version,
                      "exchange_at": self._model_exchange_at
                    }
        
        storage_info = {"storage_type": self._cloud_storage_type,
                    "access_key": access_key,
                    "secret_key": secret_key, 
                    "bucket_name": self._bucket_name}
        
        if self._cloud_storage_type == "s3":
            storage_info['region_name'] = self._config['aws']['region_name']
        else:
            storage_info['region_name'] = self._config['minio']['region_name']
            storage_info['endpoint_url'] = self._config['minio']['endpoint_url']

        
        queue_info = {"training_exchange": "", 
                      "monitor_queue": ""}

        message = MessageV2(
                headers={'timestamp': time_utils.time_now(), 'message_type': Config.SERVER_INIT_RESPONSE, 'server_id': self._server_id}, 
                content=ResponseConnection(session_id, model_info, storage_info, queue_info, self._model_exchange_at, reconnect=reconnect)
        ).to_json()
        self._queue_producer.send_data(message)


    def _handle_client_notify_model(self, msg_received):
        MessageV2.print_message(msg_received)
        client_id = msg_received['headers']['client_id']
        # only update the remote local weight path, not download to the device
        self._worker_manager.add_local_update(client_id, msg_received['content'])
        # write to influx db
        self._influxdb.write_training_process_data(msg_received)


    def _handle_client_notify_evaluation(self, msg_received):
        MessageV2.print_message(msg_received)

        info = msg_received['content']

        if info['performance'] > self._best_model.performance:
            self._best_model.update(info)
            self._write_record()

        info['version'] = int(re.search(r"v(\d+)", info['weight_file'].split("_")[1]).group(1))

        if self._check_stop_conditions(info):
            content = StopTraining()
            message = MessageV2(
                    headers={'timestamp': time_utils.time_now(), 'message_type': Config.SERVER_STOP_TRAINING, 'server_id': self._server_id},
                    content=content
            ).to_json()
            self._queue_producer.send_data(message)
            LOGGER.info("=" * 50)
            LOGGER.info("Stop condition met. Log out best model")
            LOGGER.info(self._best_model)
            LOGGER.info("=" * 50)

            self._is_stop_condition = True

        else:
            LOGGER.info(f"Up to testing global epoch {info['version']}. Best model is:")
            LOGGER.info(self._best_model)
            

    def _update(self, n_local_updates):
        if n_local_updates == 1:
            LOGGER.info("Only one update from client, passing the model to all other client in the network...")
            completed_worker: dict[str, Worker] = self._worker_manager.get_completed_workers()
            self._pass_one_local_model(completed_worker)

        else:
            LOGGER.info("Aggregating process...")
            completed_workers: dict[str, Worker] = self._worker_manager.get_completed_workers()
            
            # reset the state of worker in completed workers list
            for w_id, worker in completed_workers.items():
                worker.is_completed = False
                # keep track of the latest local version of worker used for cleaning task
                model_filename = worker.get_remote_weight_file_path().split('/')[-1]
                worker.update_local_version_used = int(re.search(r"v(\d+)", model_filename.split("_")[1]).group(1))

            # pass out a copy of completed worker to aggregating process
            worker_list = copy.deepcopy(completed_workers)
            self._strategy.aggregate(worker_list, self._cloud_storage)


    def _check_stop_conditions(self, info):
        for k, v in info.items():
            if k == "loss" and self._stop_conditions.get("min_loss") is not None:
                if v <= self._stop_conditions.get("min_loss"):
                    LOGGER.info(f"Stop condition: loss {v} <= {self._stop_conditions.get('min_loss')}")
                    return True
            elif k == "performance" and self._stop_conditions.get("max_performance") is not None:
                if v >= self._stop_conditions.get("max_performance"):
                    LOGGER.info(f"Stop condition: performance {v} >= {self._stop_conditions.get('max_performance')}")
                    return True
                
            elif k == "version" and self._stop_conditions.get("max_version") is not None:
                if v >= self._stop_conditions.get("max_version"):
                    LOGGER.info(f"Stop condition: version {v} >= {self._stop_conditions.get('max_version')}")
                    return True


    def _pass_one_local_model(self, completed_worker: dict [str, Worker]):
        for w_id, worker in completed_worker.items():
            LOGGER.info(w_id)
            self._strategy.avg_loss = worker.loss
            self._strategy.avg_qod = worker.qod
            self._strategy.global_model_update_data_size = worker.data_size
            worker.is_completed = False

            # download worker weight file
            remote_weight_file = worker.get_remote_weight_file_path()
            local_weight_file = worker.get_weight_file_path()
            self._cloud_storage.download(remote_file_path= remote_weight_file, 
                                        local_file_path= local_weight_file)

            # keep track of the latest local version of worker used for cleaning task
            model_filename = remote_weight_file.split('/')[-1]
            worker.update_local_version_used = int(re.search(r"v(\d+)", model_filename.split("_")[1]).group(1))


        # copy the worker model weight to the global model folder
        import shutil
        save_location = Config.TMP_GLOBAL_MODEL_FOLDER + self._strategy.get_new_global_model_filename()
        # LOGGER.info(save_location)
        shutil.copy(local_weight_file, save_location)


    def _write_record(self):
        folder_name = "best_model"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        # write the record of best model
        data = {
            "filename": self._best_model.model_name,
            "performance": self._best_model.performance,
            "loss": self._best_model.loss
        }
        with open(f"{folder_name}/{self._server_id}.json", "w") as file:
            json.dump(data, file)

    