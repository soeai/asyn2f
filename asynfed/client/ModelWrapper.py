from abc import abstractmethod, ABC


class ModelWrapper(ABC):
    def __int__(self, model, local_data_size: int, train_ds, test_ds, evaluate_ds=None):
        pass

    @abstractmethod
    def set_weights(self, weights):
        pass

    @abstractmethod
    def get_weights(self):
        pass

    @abstractmethod
    def train(self):
        pass

    @abstractmethod
    def evaluate(self, test_dataset):
        pass

    @abstractmethod
    def train_steps(self):
        pass

    @abstractmethod
    def test_steps(self):
        pass