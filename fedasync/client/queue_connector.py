
from pika import BlockingConnection
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties



class QueueConnector:
    def __init__(self, queue_connection: BlockingConnection) -> None:
        pass
    """
    """

    def get_msg(self):
        pass
    
    def send_to_server(self, msg: str):
        pass


