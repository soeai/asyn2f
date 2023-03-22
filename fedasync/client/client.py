from abc import ABC, abstractmethod
from queue_connector import AsynRabbitMQConsumer
from model import ClientModel
import json


class Client(ABC):
    """
    - This is the abstract Client class
    - Client can extend to use with Deep frameworks like tensorflow, pytorch by extending this abstract class and 
        implement it's abstract methods. 
    """

    def __init__(self, queue_connection: BlockingConnection) -> None:
        super().__init__()

        # Dependencies
        self.queue_connector: QueueConnector = QueueConnector(queue_connection)

    def join_server(self) -> None:
        """
        - Implement the logic for client here.
        """
        pass

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

    @abstractmethod
    def data_preprocessing(self):
        pass

    @abstractmethod
    def create_model(self):
        pass


class AsynRabbitMQConsumerImpl(AsynRabbitMQConsumer):
    def on_message(self, _unused_channel, basic_deliver, properties, body):
        msg = json.loads(body)
        print(msg)
        self.acknowledge_message(basic_deliver.delivery_tag)


def start_client(client: ClientModel, queue_config):
    queue = AsynRabbitMQConsumerImpl(queue_config['url'],
                                     queue_config['queuename'],
                                     queue_config['routingkey'],
                                     queue_config['exchange'])

    queue.run()

    print('DO TRAINING HERE')
    client.train()
    # sent notify
