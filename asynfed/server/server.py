
# Standard library imports
from datetime import datetime
from threading import Thread, Lock
from time import sleep
import concurrent.futures
import copy
import json
import logging
import os
import sys
import uuid
from abc import abstractmethod, ABC


# Third party imports
from asynfed.common.config import CloudStoragePath, LocalStoragePath, MessageType
from asynfed.common.messages.client import ClientInitConnection, ClientModelUpdate, NotifyEvaluation, TesterRequestStop
from asynfed.common.messages.server import GlobalModel, ServerModelUpdate, PingToClient, ServerRequestStop
from asynfed.common.messages.server.server_response_to_init import ModelInfo, StorageInfo 
from asynfed.common.queue_connectors import AmqpConsumer, AmqpProducer

from asynfed.common.messages import ExchangeMessage
import asynfed.common.messages as message_utils
import asynfed.common.utils.time_ultils as time_utils
import asynfed.common.utils.storage_cleaner as storage_cleaner

# Local imports
from .config_structure import ServerConfig
from .objects import BestModel, Worker

from .monitor.influxdb import InfluxDB
from .strategies import Strategy, Asyn2fStrategy, KAFLMStepStrategy
from .worker_manager import WorkerManager
from .storage_connectors import ServerStorageBoto3, ServerStorageAWS, ServerStorageMinio



thread_pool_ref = concurrent.futures.ThreadPoolExecutor
lock = Lock()

LOGGER = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
LOGGER.setLevel(logging.INFO)

class Server(ABC):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """
    def __init__(self, config: dict):
        """
        config structure can be found at server_config.py file

        """
        super().__init__()

        # load config info 
        self._config: ServerConfig = self._load_config_info(config= config)
        # get local and cloud storage path
        # global_model structure: {global_folder}/{model_name}/{version}.{file_extension}

        global_model_root_folder: str = f"{self._config.cloud_storage.global_model_root_folder}/{self._config.model_config.name}"
        self._local_storage_path: LocalStoragePath = self._get_local_storage_path()
        self._cloud_storage_path: CloudStoragePath = CloudStoragePath(global_model_root_folder= global_model_root_folder,
                                                    client_model_root_folder= self._config.cloud_storage.client_model_root_folder,)

        LOGGER.info("All configs on server")
        message_utils.print_message(self._config.to_dict())


        # boolean variable to check the exit condition
        self._stop_condition_is_met: bool = False

        # initialize an object to save best model info
        self._best_model: BestModel = BestModel()

        # Initialize dependencies
        self._strategy: Strategy = self._set_up_strategy()

        self._cloud_storage = self._set_up_cloud_storage()
        self._worker_manager: WorkerManager = WorkerManager()
        # self._influxdb: InfluxDB = InfluxDB(self._config['influxdb'])

        # queue
        # put self in to handle message from client (on_message_received)
        self._queue_consumer: AmqpConsumer = AmqpConsumer(self._config.queue_consumer, self)
        self._queue_producer: AmqpProducer = AmqpProducer(self._config.queue_producer)


        # -------------  Thread --------------
        self._consumer_thread = Thread(target= self._start_consumer, name="server_consumer_thread")
        self._consumer_thread.daemon = True

        # ping thread
        self._ping_thread = Thread(target= self._ping, name= "server_ping_thread")
        self._ping_thread.daemon = True

        # clean storage thread
        self._clean_storage_thread = Thread(target= self._clean_storage, name="server_clean_storage_thread")
        self._clean_storage_thread.daemon = True

        # -------------  Thread --------------


        # Log out ìno of the server
        LOGGER.info("=" * 40)
        LOGGER.info(f'Load all config and dependencies complete. Server {self._config.server_id} ready for training process!')
        LOGGER.info(f'Strategy: {self._config.strategy.name} with m = {self._config.strategy.m}, n = {self._config.strategy.n}')
        LOGGER.info(f'S3 Bucket: {self._config.cloud_storage.bucket_name}')
        LOGGER.info(f'Model ID: {self._strategy.model_name}')
        LOGGER.info("=" * 40)
        LOGGER.info(f'Consumer Queue')
        message_utils.print_message(self._config.queue_consumer.to_dict())
        LOGGER.info(f'Producer Queue')
        message_utils.print_message(self._config.queue_producer.to_dict()) 


    def _start_threads(self):
        self._consumer_thread.start()
        self._ping_thread.start()
        self._clean_storage_thread.start()


    @abstractmethod
    def start(self):
        pass

    # function for queue consumer to call
    # handling when receiving message
    @abstractmethod
    def _respond_connection(self, message):
        pass

    @abstractmethod
    def _handle_client_notify_model(self, message):
        pass

    @abstractmethod
    def _handle_client_notify_evaluation(self, message):
        pass

    @abstractmethod
    def _handle_client_ping(self, message):
        pass


    def on_message_received(self, ch, method, props, body):
        msg_received = message_utils.deserialize(body.decode('utf-8'))
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # when the server receive the message from client
        # update the timestamp of the client 
        # so that timestamp accross geographical regions could be consistent
        msg_received['headers']['timestamp'] = now

        # Format the datetime object as a string and return it
        msg_type = msg_received['headers']['message_type']

        if msg_type == MessageType.CLIENT_INIT_MESSAGE:
            self._respond_connection(msg_received)
        elif msg_type == MessageType.CLIENT_NOTIFY_MESSAGE:
            self._handle_client_notify_model(msg_received)
        elif msg_type == MessageType.CLIENT_NOTIFY_EVALUATION:
            self._handle_client_notify_evaluation(msg_received)
        elif msg_type == MessageType.CLIENT_PING_MESSAGE:
            self._handle_client_ping(msg_received)
            # message_utils.print_message(msg_received)
            # self._worker_manager.update_worker_last_ping(msg_received['headers']['client_id'])



    
    def _load_config_info(self, config: dict) -> ServerConfig:
        bucket_name = config['cloud_storage']['bucket_name']
        strategy = config['strategy']['name']
        config['server_id'] = config.get("server_id") or f"server-{bucket_name}"
        config['server_id'] = f"{strategy}-{config['server_id']}"
        
        config['model_config']['name'] = config['model_config']['name'] or config['server_id']

        # for multiple user to run on the same queue, 
        # set bucket name to be the queue name
        # and also the queue exchange name
        # user may already set in the run file, but just to make sure that it is set
        queue_exchange = f"{bucket_name}"
        server_consume_queue_name =  f"server-listen-queue-{queue_exchange}"
        server_publish_queue_name = f"server-publish-queue-{queue_exchange}"

        config['queue_consumer']['queue_name'] = config['queue_consumer']['queue_name'] or server_consume_queue_name
        config['queue_producer']['queue_name'] = config['queue_producer']['queue_name'] or server_publish_queue_name

        if not config['queue_consumer']['queue_exchange']:
            config['queue_consumer']['queue_exchange'] = queue_exchange
            config['queue_producer']['queue_exchange'] = queue_exchange

        return ServerConfig(**config)


    def _check_client_identity_when_joining(self, msg_received: dict):

        content: dict = msg_received['content']
        client_init_message: ClientInitConnection = ClientInitConnection(**content)

        client_id: str = msg_received['headers']['client_id']
        session_id: str = msg_received['headers']['session_id']

        if session_id in self._worker_manager.list_sessions():
            reconnect = True
            worker = self._worker_manager.get_worker_by_id(client_id)
        else:
            session_id = str(uuid.uuid4())
            # new entry
            reconnect = False
            access_key, secret_key = self._cloud_storage.get_client_key()
            worker = Worker(
                    session_id=session_id,
                    worker_id=client_id,
                    sys_info=client_init_message.system_info.to_dict(),
                    data_size=client_init_message.data_description.size,
                    qod=client_init_message.data_description.qod,
                    cloud_access_key= access_key, cloud_secret_key= secret_key
                    )

            # add to the worker manager 
            self._worker_manager.add_worker(worker)

            # create a local folder name to store weight file of worker
            client_folder_name = os.path.join(self._local_storage_path.LOCAL_MODEL_ROOT_FOLDER, worker.worker_id)
            if not os.path.exists(client_folder_name):
                os.makedirs(client_folder_name)

        LOGGER.info("*" * 20)
        LOGGER.info(worker)
        LOGGER.info("*" * 20)
        return session_id, reconnect


    def _get_local_storage_path(self) -> LocalStoragePath:
        # create local folder for storage
        # get the current folder path, then save all local file within the current folder
        server_storage_folder_name = f"{self._config.server_id}-record"
        full_path = os.path.join(os.getcwd(), server_storage_folder_name)
        return LocalStoragePath(root_folder= full_path, save_log= self._config.save_log)


    def _publish_new_global_model(self):
        # increment the current version to 1
        self._strategy.current_version += 1
        LOGGER.info("*" * 20)
        LOGGER.info(f"CURRENT GLOBAL MODEL VERSION TO BE PUBLISHED: {self._strategy.current_version}")
        LOGGER.info("*" * 20)

        current_global_model_filename = self._strategy.get_current_global_model_filename()
        local_filename = os.path.join(self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, current_global_model_filename)

        # for the cloud storage, always use forward slash
        # regardless of os
        remote_filename = f"{self._cloud_storage_path.GLOBAL_MODEL_ROOT_FOLDER}/{current_global_model_filename}"

        upload_success = self._cloud_storage.upload(local_filename, remote_filename)

        if upload_success:
            headers: dict = self._create_headers(message_type= MessageType.SERVER_NOTIFY_MESSAGE)

            global_model = GlobalModel(version= self._strategy.current_version,
                                       total_data_size= self._strategy.global_model_update_data_size,
                                       avg_loss= self._strategy.avg_loss, avg_qod= self._strategy.avg_qod)
            # global_model = GlobalModel(name= self._strategy.model_name, version= self._strategy.current_version,
            #                            total_data_size= self._strategy.global_model_update_data_size,
            #                            avg_loss= self._strategy.avg_loss, avg_qod= self._strategy.avg_qod)

            server_model_update: ServerModelUpdate = ServerModelUpdate(worker_id=[], global_model= global_model.to_dict())
            
            message = ExchangeMessage(headers= headers, content= server_model_update).to_json()

            self._queue_producer.send_data(message)
            
        else:
            LOGGER.info("-" * 40)
            LOGGER.warning(f"Fail to upload model {current_global_model_filename} to the cloud storage. Not sending update new model message to clients")
            LOGGER.info("-" * 40)


    def _set_up_cloud_storage(self) -> ServerStorageBoto3:
        self._aws_s3 = False
        if self._config.cloud_storage.type == "aws_s3":
            self._aws_s3 = True
            cloud_config = self._config.cloud_storage.aws_s3

        elif self._config.cloud_storage.type == "minio":
            cloud_config = self._config.cloud_storage.minio

        else:
            LOGGER.info("There is no cloud storage")
            sys.exit(0)

        cloud_config.storage_type = self._config.cloud_storage.type
        cloud_config.bucket_name = self._config.cloud_storage.bucket_name
        cloud_config.region_name = self._config.cloud_storage.region_name

        cloud_storage_info: StorageInfo = StorageInfo(**cloud_config.to_dict())

        if self._aws_s3:
            cloud_storage: ServerStorageAWS = ServerStorageAWS(cloud_storage_info)
        else:
            cloud_storage: ServerStorageMinio = ServerStorageMinio(cloud_storage_info)
            cloud_storage.set_client_key(client_access_key= cloud_config.client_access_key,
                                         client_secret_key= cloud_config.client_secret_key)
            
        cloud_storage.load_model_config(global_model_root_folder= self._cloud_storage_path.GLOBAL_MODEL_ROOT_FOLDER,
                                        initial_model_path= self._config.model_config.initial_model_path,
                                        file_extension= self._config.model_config.file_extension
                                        )
        return cloud_storage

    def _set_up_strategy(self) -> Strategy:
        strategy = self._config.strategy.name.lower()
        model_name = self._config.model_config.name
        strategy_object: Strategy
        if strategy == "asyn2f":
            strategy_object = Asyn2fStrategy(model_name= model_name, file_extension= self._config.model_config.file_extension)
        elif strategy == "kafl":
            strategy_object = KAFLMStepStrategy(model_name= model_name, file_extension= self._config.model_config.file_extension)
        else:
            LOGGER.info("*" * 20)
            LOGGER.info(f"The framework has not yet support the strategy you choose ({strategy})")
            LOGGER.info("Please choose either Asyn2F, KALMSTEP, or FedAvg (not case sensitive)")
            LOGGER.info("*" * 20)
            sys.exit(0)
        return strategy_object
    

    def _start_consumer(self):
        self._queue_consumer.start()


    def _ping(self):
        while True:
            for client_id in self._worker_manager.list_connected_workers():
                LOGGER.info(f'Ping to client {client_id}')
                headers: dict = self._create_headers(message_type= MessageType.SERVER_PING_TO_CLIENT)
                pint_to_client: PingToClient = PingToClient(client_id= client_id)
                message = ExchangeMessage(headers= headers, content= pint_to_client.to_dict()).to_json()
                self._queue_producer.send_data(message)
            sleep(self._config.ping_period)



    def _clean_storage(self):
        while True:
            sleep(self._config.cleaning_config.clean_storage_period)
            LOGGER.info("CLEANING TIME")

            # -------- Global Weight File Cleaning ------------ 
            current_global_version = self._strategy.current_version
            global_threshold = current_global_version - self._config.cleaning_config.global_keep_version_num

            if self._best_model.model_name != "":
                best_model_name = self._best_model.model_name
                best_global_model_version = self._strategy.extract_model_version(best_model_name)
            else:
                best_global_model_version = None
            
            # delete remote files
            storage_cleaner.delete_remote_files(cloud_storage= self._cloud_storage,
                                    folder_path= self._cloud_storage_path.GLOBAL_MODEL_ROOT_FOLDER,
                                    threshold= global_threshold, best_version= best_global_model_version)
            
            # delete local files
            storage_cleaner.delete_local_files(folder_path= self._local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, 
                                               threshold= global_threshold, best_version= best_global_model_version)
            
            # -------- Global Weight File Cleaning ------------ 


            # -------- Client weight files cleaning -----------
            current_workers = self._worker_manager.get_all_worker()
            # get a deep copy of the list of current worker in the framework
            workers = copy.deepcopy(current_workers)
            
            for w_id, worker in workers.items():
                client_threshold = worker.update_local_version_used - self._config.cleaning_config.local_keep_version_num

                # delete remote files
                # self._delete_remote_files(directory= w_id, threshold= client_threshold)
                client_folder = f"{self._cloud_storage_path.CLIENT_MODEL_ROOT_FOLDER}/{w_id}"
                storage_cleaner.delete_remote_files(cloud_storage= self._cloud_storage, folder_path= client_folder,
                                                    threshold= client_threshold)

                # delete local files
                local_directory = os.path.join(self._local_storage_path.LOCAL_MODEL_ROOT_FOLDER, w_id)
                storage_cleaner.delete_local_files(folder_path= local_directory, threshold= client_threshold)
            # -------- Client weight files cleaning -----------



    def _check_stop_conditions(self, info: dict):
        for k, v in info.items():
            if k == "loss" and self._config.model_config.stop_conditions.min_loss is not None:
                if v <= self._config.model_config.stop_conditions.min_loss:
                    LOGGER.info(f"Stop condition: loss {v} <= {self._config.model_config.stop_conditions.min_loss}")
                    return True
            elif k == "performance" and self._config.model_config.stop_conditions.max_performance is not None:
                if v >= self._config.model_config.stop_conditions.max_performance:
                    LOGGER.info(f"Stop condition: performance {v} >= {self._config.model_config.stop_conditions.max_performance}")
                    return True
                
            elif k == "version" and self._config.model_config.stop_conditions.max_version is not None:
                if v >= self._config.model_config.stop_conditions.max_version:
                    LOGGER.info(f"Stop condition: version {v} >= {self._config.model_configstop_conditions.max_version}")
                    return True



    def _write_record(self):
        folder_name = f"{self._config.server_id}-record/best_model"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        # write the record of best model
        data = {
            "filename": self._best_model.model_name,
            "performance": self._best_model.performance,
            "loss": self._best_model.loss
        }
        with open(f"{folder_name}/{self._config.server_id}.json", "w") as file:
            json.dump(data, file)


    def _create_headers(self, message_type: str) -> dict:
        headers = {'timestamp': time_utils.time_now(), 'message_type': message_type, 'server_id': self._config.server_id}
        return headers

