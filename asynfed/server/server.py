
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
# from abc import abstractmethod, ABC


# Third party imports
from asynfed.common.config import CloudStoragePath, LocalStoragePath, MessageType
from asynfed.common.messages.client import ClientInitConnection, ClientModelUpdate, NotifyEvaluation, TesterRequestStop
from asynfed.common.messages.server import GlobalModel, ServerModelUpdate, PingToClient, ServerRequestStop
from asynfed.common.messages.server.server_response_to_init import ModelInfo, StorageInfo, ServerRespondToInit
from asynfed.common.queue_connectors import AmqpConsumer, AmqpProducer

from asynfed.common.messages import ExchangeMessage
import asynfed.common.messages as message_utils
import asynfed.common.utils.time_ultils as time_utils
import asynfed.common.utils.storage_cleaner as storage_cleaner

# Local imports
from .config_structure import ServerConfig
from .objects import BestModel, Worker

from .monitor.influxdb import InfluxDB
from .strategies import Strategy, Asyn2fStrategy, KAFLMStepStrategy, FedAvgStrategy
from .worker_manager import WorkerManager
from .storage_connectors import ServerStorageBoto3, ServerStorageAWS, ServerStorageMinio



thread_pool_ref = concurrent.futures.ThreadPoolExecutor
lock = Lock()

LOGGER = logging.getLogger(__name__)
logging.getLogger("pika").setLevel(logging.WARNING)
LOGGER.setLevel(logging.INFO)

class ManageTrainingTime(object):
    def __init__(self, max_time: int):
        self.max_time = max_time
        self.start_time = None
        self.max_time_is_reach = False

    def begin_timing(self):
        self.start_time = time_utils.time_now()

    def is_max_time_reach(self, timing):
        t_diff = time_utils.time_diff(timing, self.start_time)
        if t_diff >= self.max_time:
            return True
        return False


# class Server(ABC):
class Server(object):
    """
    - This is the abstract class for server, we delegate the stop condition to be decided by user.
    - Extend this Server class and implement the stop condition methods.
    """
    def __init__(self, config: dict):
        """
        config structure can be found at server_config.py file

        """
        super().__init__()
        # self.lock = Lock()

        # load config info 
        self.config: ServerConfig = self._load_config_info(config= config)

        if self.config.model_config.stop_conditions.max_time:
            self._is_first_client = True
            self.manage_training_time = ManageTrainingTime(max_time= self.config.model_config.stop_conditions.max_time)

        # get local and cloud storage path
        # global_model structure: {global_folder}/{model_name}/{version}.{file_extension}

        global_model_root_folder: str = f"{self.config.cloud_storage.global_model_root_folder}/{self.config.model_config.name}"
        self.local_storage_path: LocalStoragePath = self._get_local_storage_path()
        self._cloud_storage_path: CloudStoragePath = CloudStoragePath(global_model_root_folder= global_model_root_folder,
                                                    client_model_root_folder= self.config.cloud_storage.client_model_root_folder,)

        LOGGER.info("All configs on server")
        message_utils.print_message(self.config.to_dict())


        # boolean variable to check the exit condition
        self.stop_condition_is_met: bool = False

        # initialize an object to save best model info
        self._best_model: BestModel = BestModel()

        # Initialize dependencies
        self._strategy: Strategy = self._set_up_strategy()

        self.cloud_storage = self._set_up_cloud_storage()
        self.worker_manager: WorkerManager = WorkerManager()
        # self.worker_manager: WorkerManager = WorkerManager(lock= self.lock)
        # self._influxdb: InfluxDB = InfluxDB(self.config['influxdb'])

        # queue
        # put self in to handle message from client (on_message_received)
        self._queue_consumer: AmqpConsumer = AmqpConsumer(self.config.queue_consumer, self)
        self._queue_producer: AmqpProducer = AmqpProducer(self.config.queue_producer)


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
        LOGGER.info(f'Load all config and dependencies complete. Server {self.config.server_id} ready for training process!')
        LOGGER.info(f'Strategy: {self.config.strategy.name} with m = {self.config.strategy.m}, n = {self.config.strategy.n}')
        LOGGER.info(f'S3 Bucket: {self.config.cloud_storage.bucket_name}')
        LOGGER.info(f'Model ID: {self._strategy.model_name}')
        LOGGER.info("=" * 40)
        LOGGER.info(f'Consumer Queue')
        message_utils.print_message(self.config.queue_consumer.to_dict())
        LOGGER.info(f'Producer Queue')
        message_utils.print_message(self.config.queue_producer.to_dict()) 


    def _start_threads(self):
        self._consumer_thread.start()
        self._ping_thread.start()
        self._clean_storage_thread.start()


    def start(self):
        # self._strategy.start_server()
        self._start_threads()
        self._strategy.handle_aggregating_process()



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


    def _handle_client_notify_model(self, message):
        self._strategy.handle_client_notify_model(message= message)

    # function for queue consumer to call
    # handling when receiving message
    def _respond_connection(self, message: dict):
        message_utils.print_message(message)

        session_id, reconnect = self.check_client_identity_when_joining(message)
        client_id: str = message['headers']['client_id']
        access_key, secret_key = self.cloud_storage.get_client_key()

        # notify newest global model to worker
        model_url = self.cloud_storage.get_newest_global_model()

        # always use forward slash for the cloud storage regardless os
        model_version = self._strategy.extract_model_version(folder_path= model_url)

        # update the current version for the strategy 
        # if the server is just on the first round
        if self._strategy.current_version == None:
            self._strategy.current_version = model_version

        # model info
        exchange_at= self.config.model_config.model_exchange_at.to_dict()


        model_info: ModelInfo = ModelInfo(global_folder= self.config.cloud_storage.global_model_root_folder, 
                                          learning_rate= self._strategy.get_learning_rate(),
                                          name= self.config.model_config.name, version=self._strategy.current_version,
                                          file_extension= self._strategy.file_extension, exchange_at= exchange_at)
        
        # check the correctness of message when sending
        message_utils.print_message(model_info.to_dict())

        client_folder = f"{self._cloud_storage_path.CLIENT_MODEL_ROOT_FOLDER}/{client_id}"

        # storage info
        storage_info: StorageInfo = StorageInfo(type= self.config.cloud_storage.type,
                                                access_key= access_key, secret_key= secret_key, 
                                                bucket_name= self.config.cloud_storage.bucket_name,
                                                region_name= self.config.cloud_storage.region_name,
                                                client_upload_folder= client_folder)

        if not self._aws_s3:
            storage_info.endpoint_url = self.config.cloud_storage.minio.endpoint_url


        # send message
        headers: dict = self._create_headers(message_type= MessageType.SERVER_INIT_RESPONSE)
        headers['session_id'] = session_id
        headers['reconnect'] = reconnect
        headers['client_id'] = client_id

        response_to_init: ServerRespondToInit = ServerRespondToInit(strategy= self.config.strategy.name,
                                                    epoch_update_frequency= self.config.strategy.n,
                                                    model_info= model_info.to_dict(),
                                                    storage_info= storage_info.to_dict())
        

        message_utils.print_message(response_to_init.to_dict())
        message= ExchangeMessage(headers= headers, content= response_to_init.to_dict()).to_json()
        self._queue_producer.send_data(message)

        # check whether it is first client to begin timing
        if self._is_first_client:
            LOGGER.info("*" * 50)
            LOGGER.info("First client join. About to set first join time to keep track of ")
            LOGGER.info("*" * 50)
            self._is_first_client = False
            self.manage_training_time.begin_timing()


    def _handle_client_notify_evaluation(self, message):
        message_utils.print_message(message)
        model_evaluation: NotifyEvaluation = NotifyEvaluation(**message['content'])

        if model_evaluation.performance > self._best_model.performance:
            self._best_model.update(model_evaluation)
            self._write_record()

        model_evaluation.version = self._strategy.extract_model_version(model_evaluation.remote_storage_path)
        model_evaluation_dict = model_evaluation.to_dict()

        if self._check_stop_conditions(model_evaluation_dict):
            headers: dict = self._create_headers(message_type= MessageType.SERVER_STOP_TRAINING)
            require_to_stop: ServerRequestStop = ServerRequestStop()

            message = ExchangeMessage(headers= headers, content= require_to_stop.to_dict()).to_json()
            self._queue_producer.send_data(message)
            LOGGER.info("=" * 50)
            LOGGER.info("Stop condition met. Log out best model")
            LOGGER.info(self._best_model)
            LOGGER.info("=" * 50)

            self.stop_condition_is_met = True

        else:
            LOGGER.info(f"Up to testing global epoch {model_evaluation.version}. Best model is:")
            LOGGER.info(self._best_model)


    def _handle_client_ping(self, message):
        message_utils.print_message(message)
        self.worker_manager.update_worker_last_ping(message['headers']['client_id'])


    
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


    def check_client_identity_when_joining(self, msg_received: dict):

        content: dict = msg_received['content']
        client_init_message: ClientInitConnection = ClientInitConnection(**content)

        client_id: str = msg_received['headers']['client_id']
        session_id: str = msg_received['headers']['session_id']

        if session_id in self.worker_manager.list_sessions():
            reconnect = True
            worker = self.worker_manager.get_worker_by_id(client_id)
        else:
            session_id = str(uuid.uuid4())
            # new entry
            reconnect = False
            access_key, secret_key = self.cloud_storage.get_client_key()
            worker = Worker(
                    session_id=session_id,
                    worker_id=client_id,
                    sys_info=client_init_message.system_info.to_dict(),
                    data_size=client_init_message.data_description.size,
                    qod=client_init_message.data_description.qod,
                    cloud_access_key= access_key, cloud_secret_key= secret_key
                    )

            # add to the worker manager 
            self.worker_manager.add_worker(worker)

            # create a local folder name to store weight file of worker
            client_folder_name = os.path.join(self.local_storage_path.LOCAL_MODEL_ROOT_FOLDER, worker.worker_id)
            if not os.path.exists(client_folder_name):
                os.makedirs(client_folder_name)

        LOGGER.info("*" * 20)
        LOGGER.info(worker)
        LOGGER.info("*" * 20)
        return session_id, reconnect


    def _get_local_storage_path(self) -> LocalStoragePath:
        # create local folder for storage
        # get the current folder path, then save all local file within the current folder
        server_storage_folder_name = f"{self.config.server_id}-record"
        full_path = os.path.join(os.getcwd(), server_storage_folder_name)
        return LocalStoragePath(root_folder= full_path, save_log= self.config.save_log)


    # def _check_max_time_is_reached(self):
    #     if self.manage_training_time.is_max_time_reach(time_utils.time_now()):
            # headers: dict = self._create_headers(message_type= MessageType.SERVER_STOP_TRAINING)
            # require_to_stop: ServerRequestStop = ServerRequestStop()

            # message = ExchangeMessage(headers= headers, content= require_to_stop.to_dict()).to_json()
            # self._queue_producer.send_data(message)
            # LOGGER.info("=" * 50)
            # LOGGER.info("Stop condition met. Log out best model")
            # LOGGER.info(self._best_model)
            # LOGGER.info("=" * 50)


    def _handle_when_max_time_is_reached(self):
        # to sifnify that when receiving notifying the last global model acc from tester
        LOGGER.info("*" * 60)
        LOGGER.info("Set max version to be the current version of global model")
        previous_version_setting = self.config.model_config.stop_conditions.max_version
        self.config.model_config.stop_conditions.max_version = self._strategy.current_version
        LOGGER.info(f"current max version setting: {previous_version_setting}, new current version: {self.config.model_config.stop_conditions.max_version}")
        LOGGER.info("*" * 60)
        
        # send stop message for trainer to stop training
        headers: dict = self._create_headers(message_type= MessageType.SERVER_STOP_TRAINING)
        require_to_stop: ServerRequestStop = ServerRequestStop()
        message = ExchangeMessage(headers= headers, content= require_to_stop.to_dict()).to_json()
        self._queue_producer.send_data(message)



    def publish_new_global_model(self):
        # increment the current version to 1
        self._strategy.current_version += 1

        # check whether max time is reach
        if self.manage_training_time:
            if self.manage_training_time.is_max_time_reach(time_utils.time_now()):
                LOGGER.info("Max training time is reached. Shortly the program will be close after receiving the accuracy of the last global model from tester.")
                self._handle_when_max_time_is_reached()
                # self.stop_condition_is_met = True

        LOGGER.info("*" * 20)
        LOGGER.info(f"CURRENT GLOBAL MODEL VERSION TO BE PUBLISHED: {self._strategy.current_version}")
        LOGGER.info("*" * 20)

        current_global_model_filename = self._strategy.get_current_global_model_filename()
        local_filename = os.path.join(self.local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, current_global_model_filename)

        # for the cloud storage, always use forward slash
        # regardless of os
        remote_filename = f"{self._cloud_storage_path.GLOBAL_MODEL_ROOT_FOLDER}/{current_global_model_filename}"

        upload_success = self.cloud_storage.upload(local_filename, remote_filename)

        if upload_success:
            headers: dict = self._create_headers(message_type= MessageType.SERVER_NOTIFY_MESSAGE)

            global_model = GlobalModel(version= self._strategy.current_version,
                                       total_data_size= self._strategy.global_model_update_data_size,
                                       avg_loss= self._strategy.avg_loss, avg_qod= self._strategy.avg_qod)
            

            learning_rate = self._strategy.get_learning_rate()

            server_model_update: ServerModelUpdate = ServerModelUpdate(worker_id=[], global_model= global_model.to_dict(),
                                                                       learning_rate= learning_rate)
            

            message = ExchangeMessage(headers= headers, content= server_model_update).to_json()


            self._queue_producer.send_data(message)
            
        else:
            LOGGER.info("-" * 40)
            LOGGER.warning(f"Fail to upload model {current_global_model_filename} to the cloud storage. Not sending update new model message to clients")
            LOGGER.info("-" * 40)


    def _set_up_cloud_storage(self) -> ServerStorageBoto3:
        self._aws_s3 = False
        if self.config.cloud_storage.type == "aws_s3":
            self._aws_s3 = True
            cloud_config = self.config.cloud_storage.aws_s3

        elif self.config.cloud_storage.type == "minio":
            cloud_config = self.config.cloud_storage.minio

        else:
            LOGGER.info("There is no cloud storage")
            sys.exit(0)

        cloud_config.storage_type = self.config.cloud_storage.type
        cloud_config.bucket_name = self.config.cloud_storage.bucket_name
        cloud_config.region_name = self.config.cloud_storage.region_name

        cloud_storage_info: StorageInfo = StorageInfo(**cloud_config.to_dict())

        if self._aws_s3:
            cloud_storage: ServerStorageAWS = ServerStorageAWS(cloud_storage_info)
        else:
            cloud_storage: ServerStorageMinio = ServerStorageMinio(cloud_storage_info)
            cloud_storage.set_client_key(client_access_key= cloud_config.client_access_key,
                                         client_secret_key= cloud_config.client_secret_key)
            
        cloud_storage.load_model_config(global_model_root_folder= self._cloud_storage_path.GLOBAL_MODEL_ROOT_FOLDER,
                                        initial_model_path= self.config.model_config.initial_model_path,
                                        file_extension= self.config.model_config.file_extension
                                        )
        return cloud_storage

    def _set_up_strategy(self) -> Strategy:
        strategy = self.config.strategy.name.lower()
        model_name = self.config.model_config.name
        strategy_object: Strategy
        if strategy == "asyn2f":
            strategy_object = Asyn2fStrategy(server= self, model_name= model_name, file_extension= self.config.model_config.file_extension,
                                             m = self.config.strategy.m, 
                                             initial_learning_rate= self.config.model_config.synchronous_learning_rate.initial_learning_rate,
                                             total_update_times= self.config.model_config.synchronous_learning_rate.total_update_times)
        elif strategy == "kafl":
            strategy_object = KAFLMStepStrategy(server= self, model_name= model_name, file_extension= self.config.model_config.file_extension,
                                                m = self.config.strategy.m, 
                                                initial_learning_rate= self.config.model_config.synchronous_learning_rate.initial_learning_rate,
                                                total_update_times= self.config.model_config.synchronous_learning_rate.total_update_times)
        elif strategy == "fedavg":
            print(f"This is inside: {self.config.strategy.use_loss}")
            strategy_object = FedAvgStrategy(server= self, model_name= model_name, file_extension= self.config.model_config.file_extension,
                                            m = self.config.strategy.m, use_loss= self.config.strategy.use_loss, beta= self.config.strategy.beta,
                                            initial_learning_rate= self.config.model_config.synchronous_learning_rate.initial_learning_rate,
                                            total_update_times= self.config.model_config.synchronous_learning_rate.total_update_times)
        else:
            LOGGER.info("*" * 20)
            LOGGER.info(f"The framework has not yet support the strategy you choose ({strategy})")
            LOGGER.info("Please choose either Asyn2F or KAFL (not case sensitive)")
            LOGGER.info("*" * 20)
            sys.exit(0)
        return strategy_object
    

    def _start_consumer(self):
        self._queue_consumer.start()
        LOGGER.info("CONSUMER THREAD IS RUNNING")


    def _ping(self):
        LOGGER.info("PING THREAD IS RUNNING")
        while True:
            for client_id in self.worker_manager.list_connected_workers():
                LOGGER.info(f'Ping to client {client_id}')
                headers: dict = self._create_headers(message_type= MessageType.SERVER_PING_TO_CLIENT)
                pint_to_client: PingToClient = PingToClient(client_id= client_id)
                message = ExchangeMessage(headers= headers, content= pint_to_client.to_dict()).to_json()
                self._queue_producer.send_data(message)
            sleep(self.config.ping_period)



    def _clean_storage(self):
        LOGGER.info("CLEANING THREAD IS RUNNING!")

        print(f"{self._cloud_storage_path.GLOBAL_MODEL_ROOT_FOLDER}")
        print(f"{self._cloud_storage_path.CLIENT_MODEL_ROOT_FOLDER}")
        print(f"{self.local_storage_path.GLOBAL_MODEL_ROOT_FOLDER}")
        print(f"{self.local_storage_path.LOCAL_MODEL_ROOT_FOLDER}")

        while True:
            sleep(self.config.cleaning_config.clean_storage_period)

            LOGGER.info("CLEANING TIME")
            # -------- Global Weight File Cleaning ------------ 
            current_global_version = self._strategy.current_version or 1
            global_threshold = current_global_version - self.config.cleaning_config.global_keep_version_num

            if self._best_model.model_name != "":
                best_model_name = self._best_model.model_name
                best_global_model_version = self._strategy.extract_model_version(best_model_name)
            else:
                best_global_model_version = None
            
            # delete remote files
            storage_cleaner.delete_remote_files(cloud_storage= self.cloud_storage,
                                    folder_path= self._cloud_storage_path.GLOBAL_MODEL_ROOT_FOLDER,
                                    threshold= global_threshold, best_version= best_global_model_version)
            
            # delete local files
            storage_cleaner.delete_local_files(folder_path= self.local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, 
                                               threshold= global_threshold, best_version= best_global_model_version)
            
            # -------- Global Weight File Cleaning ------------ 


            # -------- Client weight files cleaning -----------
            current_workers = self.worker_manager.get_all_worker()
            # get a deep copy of the list of current worker in the framework
            workers = copy.deepcopy(current_workers)
            
            for w_id, worker in workers.items():
                client_threshold = worker.update_local_version_used - self.config.cleaning_config.local_keep_version_num

                # delete remote files
                # self._delete_remote_files(directory= w_id, threshold= client_threshold)
                client_folder = f"{self._cloud_storage_path.CLIENT_MODEL_ROOT_FOLDER}/{w_id}"
                storage_cleaner.delete_remote_files(cloud_storage= self.cloud_storage, folder_path= client_folder,
                                                    threshold= client_threshold)

                # delete local files
                local_directory = os.path.join(self.local_storage_path.LOCAL_MODEL_ROOT_FOLDER, w_id)
                storage_cleaner.delete_local_files(folder_path= local_directory, threshold= client_threshold)
            # -------- Client weight files cleaning -----------




    def _check_stop_conditions(self, info: dict):
        for k, v in info.items():
            if k == "performance" and self.config.model_config.stop_conditions.max_performance is not None:
                if v >= self.config.model_config.stop_conditions.max_performance:
                    LOGGER.info(f"Stop condition: performance {v} >= {self.config.model_config.stop_conditions.max_performance}")
                    return True
                
            if k == "version" and self.config.model_config.stop_conditions.max_version is not None:
                if v >= self.config.model_config.stop_conditions.max_version:
                    LOGGER.info(f"Stop condition: version {v} >= {self.config.model_config.stop_conditions.max_version}")
                    return True

            # if k == "loss" and self.config.model_config.stop_conditions.min_loss is not None:
            #     if v <= self.config.model_config.stop_conditions.min_loss:
            #         LOGGER.info(f"Stop condition: loss {v} <= {self.config.model_config.stop_conditions.min_loss}")
            #         return True

        return False


    def _write_record(self):
        folder_name = f"{self.config.server_id}-record/best_model"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        # write the record of best model
        data = {
            "filename": self._best_model.model_name,
            "performance": self._best_model.performance,
            "loss": self._best_model.loss
        }
        with open(f"{folder_name}/{self.config.server_id}.json", "w") as file:
            json.dump(data, file)


    def _create_headers(self, message_type: str) -> dict:
        headers = {'timestamp': time_utils.time_now(), 'message_type': message_type, 'server_id': self.config.server_id}
        return headers

