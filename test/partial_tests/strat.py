import uuid
from asynfed.commons.conf import Config
from asynfed.server.strategies.AsynFL import AsynFL
from asynfed.server.worker_manager import WorkerManager
from asynfed.server.objects.worker import Worker

strat = AsynFL()
strat.current_version = 1
Config.TMP_LOCAL_MODEL_FOLDER = './'
Config.TMP_GLOBAL_MODEL_FOLDER = './'
worker_manager = WorkerManager()
for i in range(2):
    worker = Worker("worker" + str(i), "", "")
    worker.weight_file = "weights.pkl"
    worker.alpha = 1
    worker.worker_id = str(uuid.uuid4())
    worker.current_version = 1
    worker_manager.add_worker(worker)
    worker_manager.worker_update_queue[worker.worker_id] = worker

# test strat.aggregate function
strat.aggregate(worker_manager.worker_pool, worker_manager.worker_update_queue)