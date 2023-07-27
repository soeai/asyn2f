from asynfed.common.messages.client import NotifyEvaluation


class BestModel:
    """
    intended to save best model
    """

    def __init__(self, model_name: str = "", performance: float = 0.0, loss: float = 1000) -> None:
        # Properties
        self.model_name = model_name
        self.performance = performance
        self.loss = loss


    def update(self, model_evaluation: NotifyEvaluation):
        self.model_name = model_evaluation.remote_storage_path
        self.loss = model_evaluation.loss
        self.performance =  model_evaluation.performance


    def __str__(self):
        """
        Implement toString function here!
        """
        return f"Model name: {self.model_name} | performance: {self.performance * 100 } | loss: {self.loss}"
