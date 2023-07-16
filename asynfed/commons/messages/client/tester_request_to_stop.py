class TesterRequestStop:
    def __init__(self, weight_file, performance, loss):
        self.weight_file = weight_file
        self.performance = performance
        self.loss = loss

    def to_dict(self) -> dict:
        return self.__dict__
