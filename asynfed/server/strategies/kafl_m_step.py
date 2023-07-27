
# from typing import Dict, List
# import os.path
# import copy
# import pickle
# import numpy as np
# from asynfed.server.objects import Worker
# from asynfed.server.storage_connector.boto3 import ServerStorageBoto3
# from asynfed.common.config import LocalStoragePath
# from asynfed.server.manager.worker_manager import WorkerManager
# from .strategy import Strategy


# import logging
# LOGGER = logging.getLogger(__name__)

# class KAFLMStepStrategy(Strategy):

#     def __init__(self, model_name: str, file_extension: str, m: int = 3, agg_hyperparam: float = 0.8):
#         """
#         Args:
#             m (int, optional): Number of workers to aggregate. Defaults to 3.
#             agg_hyperparam (float, optional): Aggregation hyperparameter. Defaults to 0.8.
#         """
#         super().__init__(model_name= model_name, file_extension= file_extension)
#         self.m = m 
#         self.agg_hyperparam = agg_hyperparam 

#     def select_client(self, all_clients) -> List [str]:
#         return all_clients
    
#     def aggregate(self, worker_manager: WorkerManager, cloud_storage: ServerStorageBoto3, 
#                   local_storage_path: LocalStoragePath):
#         LOGGER.info("Aggregating process...")
#         completed_workers: dict[str, Worker] = worker_manager.get_completed_workers()
#         if len(completed_workers) < self.m:
#             LOGGER.info(f"Aggregation is not executed because the number of completed workers is not enough. Expected {self.m} but got {len(completed_workers)}")
#             return False
        
#         # reset the state of worker in completed workers list
#         for _, worker in completed_workers.items():
#             worker.is_completed = False
#             # keep track of the latest local version of worker used for cleaning task
#             model_filename = worker.get_remote_weight_file_path().split(os.path.sep)[-1]
#             worker.update_local_version_used = self.extract_model_version(model_filename)

#         # pass out a copy of completed worker to aggregating process
#         completed_workers = copy.deepcopy(completed_workers)
#         #------
#         LOGGER.info("-" * 20)
#         LOGGER.info(f"Current global version before aggregating process: {self.current_version}")
#         LOGGER.info(f"{len(completed_workers)} workers are expected to join this aggregating round")
#         LOGGER.info("-" * 20)
#         LOGGER.info("Before aggregating takes place, check whether the file path that client provide actually exist in the cloud storage")
#         workers = self._get_valid_completed_workers(workers=completed_workers, 
#                                                     cloud_storage=cloud_storage,
#                                                     local_model_root_folder=local_storage_path.LOCAL_MODEL_ROOT_FOLDER)
#         # Store worker objects in a list
#         workers = [w_obj for _, w_obj in workers.items()]

#         # Get current global weight
#         # Check if global model is in local storage
#         remote_path = cloud_storage.get_newest_global_model()
#         filename = remote_path.split(os.path.sep)[-1]
#         local_path = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, filename)
#         if not os.path.exists(local_path):
#             cloud_storage.download(remote_file_path=remote_path, local_file_path=local_path)
#         w_g = np.array(self._get_model_weights(local_path))
#         # Execute global update 
#         ## Calculate w_new(t)
#         w_new = 0
#         w_tmp = []
#         for i in range(len(workers)):
#             w_i = np.array(self._get_model_weights(workers[i].get_weight_file_path(local_model_root_folder=local_storage_path.LOCAL_MODEL_ROOT_FOLDER)))
#             w_tmp.append(w_i)
#             w_new += (w_tmp[i]* workers[i].data_size)
#         total_num_samples = sum([workers[i].data_size for i in range(len(workers))])
#         w_new /= total_num_samples

#         ## Calculate w_g(t+1)
#         w_g_new = w_g * (1-self.agg_hyperparam) + w_new * self.agg_hyperparam


#         # Save new global model
#         save_location = os.path.join(local_storage_path.GLOBAL_MODEL_ROOT_FOLDER, self.get_new_global_model_filename())
#         with open(save_location, "wb") as f:
#             pickle.dump(w_g_new, f)


#         LOGGER.info(f"Aggregating process is completed. New global model is saved at {save_location}")
#         return True

