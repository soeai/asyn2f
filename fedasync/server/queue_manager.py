import json
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection


class QueueManager:

    def __init__(self, queue_connection: BlockingConnection) -> None:
        # Properties
        self.queue_connection: BlockingConnection

    def send_to_client(self):
        pass

    def setup_queue(self):
        pass

    def send_to_monitor_services(self):
        pass

    def get_message_from_server_queue(self):
        pass


