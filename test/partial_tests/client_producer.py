from fedasync.client.client import ClientProducer
from fedasync.commons.conf import Config
from fedasync.commons.messages.client_init_connect_to_server import ClientInit

Config.QUEUE_NAME = "client_queue"
client_prod = ClientProducer()

message = ClientInit()
message.sessionid = "teset_session_id"

client_prod.init_connect_to_server(
    message.serialize()
)
