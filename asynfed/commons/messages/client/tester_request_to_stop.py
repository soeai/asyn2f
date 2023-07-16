from asynfed.commons.messages import MessageObject
class TesterRequestStop(MessageObject):
    def __init__(self, weight_file, performance, loss):
        self.weight_file = weight_file
        self.performance = performance
        self.loss = loss

