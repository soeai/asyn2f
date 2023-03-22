from queue_connector import AsynRabbitMQConsumer
from model import ClientModel
import json


class AsynRabbitMQConsumerImpl(AsynRabbitMQConsumer):
    def on_message(self, _unused_channel, basic_deliver, properties, body):
        msg = json.loads(body)
        print(msg)
        self.acknowledge_message(basic_deliver.delivery_tag)


def start_client(client:ClientModel, queue_config):
    queue = AsynRabbitMQConsumerImpl(queue_config['url'],
                                     queue_config['queuename'],
                                     queue_config['routingkey'],
                                     queue_config['exchange'])

    queue.run()

    print('DO TRAINING HERE')
    client.train()
    # sent notify


