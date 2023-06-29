
class NotifyModel:
    def __init__(self, weight_file, global_version_used, loss, performance):
        self.weight_file = weight_file
        self.global_version_used = global_version_used
        self.loss = loss
        self.performance = performance
