
from time import sleep
from typing import Dict, List
import os.path
import copy
import re
import pickle
import numpy as np
from asynfed.server.objects import Worker
from asynfed.server.server_boto3_storage_connector import ServerStorageBoto3
from asynfed.commons.config import LocalStoragePath
from asynfed.server.worker_manager import WorkerManager
from .strategy import Strategy


import logging
LOGGER = logging.getLogger(__name__)

class MStepFedAsync(Strategy):

    def __init__(self):
        super().__init__()
        self.m = 2 # Number of workers to aggregate
        self.agg_hyperparam = 0.5 # Aggregation hyperparameter

    def select_client(self, all_clients) -> List [str]:
        return all_clients
    
    def aggregate(self, worker_manager: WorkerManager, cloud_storage: ServerStorageBoto3, 
                  local_storage_path: LocalStoragePath):
        LOGGER.info("Aggregating process...")
        completed_workers: dict[str, Worker] = worker_manager.get_completed_workers()
        if len(completed_workers) < self.m:
            LOGGER.info(f"Aggregation is not executed because the number of completed workers is not enough. Expected {self.m} but got {len(completed_workers)}")
            return False
        
        # reset the state of worker in completed workers list
        for _, worker in completed_workers.items():
            worker.is_completed = False
            # keep track of the latest local version of worker used for cleaning task
            model_filename = worker.get_remote_weight_file_path().split(os.path.sep)[-1]
            worker.update_local_version_used = self._get_model_version(model_filename)

        # pass out a copy of completed worker to aggregating process
        completed_workers = copy.deepcopy(completed_workers)
        #------
        LOGGER.info("-" * 20)
        LOGGER.info(f"Current global version before aggregating process: {self.current_version}")
        LOGGER.info(f"{len(completed_workers)} workers are expected to join this aggregating round")
        LOGGER.info("-" * 20)
        LOGGER.info("Before aggregating takes place, check whether the file path that client provide actually exist in the cloud storage")
        workers = self._get_valid_completed_workers(workers=completed_workers, 
                                                    cloud_storage=cloud_storage,
                                                    local_model_root_folder=local_storage_path.LOCAL_MODEL_ROOT_FOLDER)
        # Store worker objects in a list
        workers = [w_obj for _, w_obj in workers.items()]

        # Get current global weight
        # Check if global model is in local storage
        remote_path = cloud_storage.get_newest_global_model()
        filename = remote_path.split(os.path.sep)[-1]
        local_path = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, filename)
        if not os.path.exists(local_path):
            cloud_storage.download(remote_file_path=remote_path, local_file_path=local_path)
        w_g = np.array(self._get_model_weights(local_path))
        # Execute global update 
        ## Calculate w_new(t)
        w_new = 0
        w_tmp = []
        for i in range(len(workers)):
            w_i = np.array(self._get_model_weights(workers[i].get_weight_file_path(local_model_root_folder=local_storage_path.LOCAL_MODEL_ROOT_FOLDER)))
            w_tmp.append(w_i)
            w_new += (w_tmp[i]* workers[i].data_size)
        total_num_samples = sum([workers[i].data_size for i in range(len(workers))])
        w_new /= total_num_samples

        ## Calculate w_g(t+1)
        w_g_new = w_g * (1-self.agg_hyperparam) + w_new * self.agg_hyperparam


        # Save new global model
        save_location = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self.get_new_global_model_filename())
        with open(save_location, "wb") as f:
            pickle.dump(w_g_new, f)


        LOGGER.info(f"Aggregating process is completed. New global model is saved at {save_location}")
        return True

    def _get_valid_completed_workers(self, workers: Dict[str, Worker], cloud_storage: ServerStorageBoto3,
                                     local_model_root_folder: str) -> Dict[str, Worker]:
        valid_completed_workers = {}

        for w_id, worker in workers.items():
            remote_path = worker.get_remote_weight_file_path()
            LOGGER.info(f"{worker.worker_id} qod: {worker.qod}, loss: {worker.loss}, datasize : {worker.data_size}, weight file: {remote_path}")
            file_exists = cloud_storage.is_file_exists(file_path=remote_path)
            
            if file_exists:
                # valid_completed_workers[w_id] = worker
                LOGGER.info(f"{remote_path} exists in the cloud. Begin to download shortly")
                local_path = worker.get_weight_file_path(local_model_root_folder= local_model_root_folder)
                download_success = self._attempt_to_download(cloud_storage= cloud_storage, 
                                                             remote_file_path= remote_path, local_file_path= local_path)
                
                if download_success:
                    worker.weight_array =  self._get_model_weights(local_path)
                    valid_completed_workers[w_id] = worker

            else:
                LOGGER.info(f"worker {w_id}: weight file {remote_path} does not exist in the cloud. Remove {w_id} from aggregating process")

            LOGGER.info("*" * 20)

        return valid_completed_workers

    def _attempt_to_download(self, cloud_storage: ServerStorageBoto3, remote_file_path: str, local_file_path: str, n_attemps: int = 3) -> bool:
        for i in range(n_attemps):
            if cloud_storage.download(remote_file_path= remote_file_path, local_file_path= local_file_path, try_time=n_attemps):
                return True
            LOGGER.info(f"{i + 1} attempt: download model failed, retry in 5 seconds.")
            i += 1
            if i == n_attemps:
                LOGGER.info(f"Already try {n_attemps} time. Pass this client model: {remote_file_path}")
            sleep(5)

        return False

    def _get_model_weights(self, file_path):
        while not os.path.isfile(file_path):
            sleep(3)
        with open(file_path, "rb") as f:
            weights = pickle.load(f)
        return weights

    def _get_model_version(self, model_name: str):
        return int(re.search(r"v(\d+)", model_name.split("_")[1]).group(1))

