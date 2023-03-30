import json
import logging

from fedasync.commons.conf import Config, RoutingRules
from fedasync.commons.utils.consumer import Consumer
from fedasync.commons.utils.producer import Producer


class ClientConsumer(Consumer):
    def __init__(self):
        super().__init__()
        self.storage_access_key = None
        self.storage_secret_key = None
        self.global_model_version = None


    def setup(self):

        # declare queue
        self._channel.queue_declare(queue=Config.QUEUE_NAME)

        # binding.
        self._channel.queue_bind(
            Config.QUEUE_NAME,
            Config.TRAINING_EXCHANGE,
            RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT
        )

        self._channel.queue_bind(
            Config.QUEUE_NAME,
            Config.TRAINING_EXCHANGE,
            RoutingRules.SERVER_NOTIFY_MODEL_TO_CLIENT
        )

        self.start_consuming()

    def on_message(self, channel, basic_deliver, properties, body):
        # if message come from routing SERVER_INIT_RESPONSE_TO_CLIENT then save the model id.
        if basic_deliver.routing_key == RoutingRules.SERVER_INIT_RESPONSE_TO_CLIENT:
            decoded = json.loads(bytes.decode(body))
            print(f'Init connection to the server successfully | access_key: {decoded["access_key"]} | secret_key: {decoded["secret_key"]} | model_url: {decoded["model_url"]}')
            self.storage_access_key = decoded["access_key"]
            self.storage_secret_key = decoded["secret_key"]
            self.global_model_version = decoded["model_url"]

        else:
            print(body)
            logging.info(body)


class ClientProducer(Producer):
    def __init__(self):
        super().__init__()

    def notify_model_to_server(self, message):
        self.publish_message(
            RoutingRules.CLIENT_NOTIFY_MODEL_TO_SERVER,
            message
        )

    def init_connect_to_server(self, message):
        self.publish_message(
            RoutingRules.CLIENT_INIT_SEND_TO_SERVER,
            message
        )



