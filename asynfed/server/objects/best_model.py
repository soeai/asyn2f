from asynfed.commons.conf import Config
# from asynfed.commons.messages.client_init_connect_to_server import SysInfo
from asynfed.commons.messages import SysInfo
from asynfed.commons.utils.time_ultils import time_now


class BestModel:
    """
    intended to save best model
    """

    def __init__(self, model_name: str = "", performance: float = 0.0, loss: float = 1000) -> None:
        # Properties
        self.model_name = model_name
        self.performance = performance
        self.loss = loss

    def update(self, info: dict):
        self.model_name = info['weight_file']
        self.loss = info['loss']
        self.performance =  info['performance']

    def __str__(self):
        """
        Implement toString function here!
        """
        return f"Model name: {self.model_name} | performance: {self.performance * 100 } | loss: {self.loss}"
