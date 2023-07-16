from asynfed.commons.messages import MessageObject

class NotifyEvaluation(MessageObject):
    def __init__(self, weight_file: str, performance: float, loss: float):
        self.weight_file = weight_file
        self.performance = performance
        self.loss = loss

