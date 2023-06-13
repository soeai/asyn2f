from abc import abstractmethod, ABC


class ModelWrapper(ABC):
    # model, data_size, train_ds is require
    # test_ds is optional

    def __int__(self, model, data_size, qod, train_ds, test_ds):
        pass

    @abstractmethod
    # input: a list of several numpy arrays (corresponding to several layers)
    # expected result: set it to be the weights of the model
    def set_weights(self, weights):
        pass

    # output: return weights as a list of numpy array
    @abstractmethod
    def get_weights(self):
        pass

    # output: performance and loss
    @abstractmethod
    def fit(self, x, y):
        pass

    # output: precision and loss
    @abstractmethod
    def evaluate(self, x, y):
        pass
