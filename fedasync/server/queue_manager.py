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
    
    def decode(self, message):
        # Convert the message body (bytes) to a string  
        body_str = message.decode('utf-8')

        # Parse the message body string as JSON
        body = json.loads(body_str)