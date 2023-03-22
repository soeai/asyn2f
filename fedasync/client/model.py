from abc import ABC, abstractmethod


class ClientModel(ABC):
    """
    - This is the abstract Client class
    - Client can extend to use with Deep frameworks like tensorflow, pytorch by extending this abstract class and
        implement it's abstract methods.
    """

    # Abstract methods
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
    def evaluate(self):
        pass