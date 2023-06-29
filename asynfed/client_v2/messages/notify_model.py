
class NotifyModel:
    def __init__(self, remote_worker_weight_path, filename, global_version_used, loss, performance):
        self.remote_worker_weight_path = remote_worker_weight_path
        self.filename = filename
        self.global_version_used = global_version_used
        self.loss = loss
        self.performance = performance
