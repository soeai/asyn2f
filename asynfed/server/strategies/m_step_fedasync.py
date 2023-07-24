
from time import sleep
from typing import Dict, List
import os.path
import pickle
from asynfed.server.objects import Worker
from asynfed.server.server_boto3_storage_connector import ServerStorageBoto3
from asynfed.commons.config import LocalStoragePath
from .strategy import Strategy

import logging
LOGGER = logging.getLogger(__name__)

class MStepFedAsync(Strategy):

    def __init__(self):
        super().__init__()
        self.m = 3 # Number of workers to aggregate
        self.agg_hyperparam = 0.5 # Aggregation hyperparameter

    def select_client(self, all_clients) -> List [str]:
        return all_clients
    
    def aggregate(self, completed_workers: Dict [str, Worker], cloud_storage: ServerStorageBoto3, 
                  local_storage_path: LocalStoragePath):
        print('local path: ', local_storage_path)
        if not len(completed_workers) == self.m:
            LOGGER.info(f"Aggregation is not executed because the number of completed workers is not enough. Expected {self.m} workers")
            return
        
        # Store worker objects in a list
        w_tmp = self._get_valid_completed_workers(workers=completed_workers, 
                                                cloud_storage=cloud_storage,
                                                    local_model_root_folder=local_storage_path.LOCAL_MODEL_ROOT_FOLDER)
        w_tmp = [w_obj for _, w_obj in w_tmp.items()]

        # Get current global weight
        w_g = self._get_model_weights(local_storage_path)

        # Execute global update 
        ## Calculate w_new(t)
        w_new = 0
        for i in range(len(w_tmp)):
            w_tmp[i].weights = self._get_model_weights(local_storage_path)
            w_new += w_tmp[i].weights * w_tmp[i].data_size
        total_num_samples = sum([w_tmp[i].data_size for i in range(len(w_tmp))])
        w_new /= total_num_samples

        ## Calculate w_g(t+1)
        w_g_new = (1-self.agg_hyperparam) * w_g + self.agg_hyperparam * w_new


        # Save new global model
        save_location = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self.get_new_global_model_filename())
        with open(save_location, "wb") as f:
            pickle.dump(w_g_new, f)

        # model_url = cloud_storage.get_newest_global_model()
        save_location = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self.get_new_global_model_filename())

        with open(save_location, "wb") as f:
            pickle.dump(w_g_new, f)


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