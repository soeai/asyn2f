

class RoutingRules:
    """
    define routing key here!
    """
    # at Client Queue
    CLIENT_REGISTER: str = "client.register"
    CLIENT_UPDATE_LOCAL: str = "client.update.local"

    # at Server Queue
    SERVER_REPLY: str = "server.reply"
    SERVER_UPDATE_GLOBAL: str = "server.update.global"


    # at Monitor Queue
    # From Client
    CLIENT_SEND_LOCAL_TRAINING: str = "client.send.local.training"
    CLIENT_SEND_RUNNING_STATUS: str = "client.send.running.status"

    # From Server
    SERVER_SEND_GLOBAL_TRAINING: str = "server.send.global.training"


class StorageConfig:
    """
    storage config here!
    """
    
    
class QueueConfig:
    """
    Queue config here!
    """
    # Queue name
    SERVER_QUEUE: str = "server_queue"
    CLIENT_QUEUE: str = "client_queue"
    MONITOR_QUEUE: str = "monitor_queue"
    
    # Echanges
    

class ServerConfig:
    """
    Server config here!
    """


class ClientConfig:
    """
    Client config here!
    """


