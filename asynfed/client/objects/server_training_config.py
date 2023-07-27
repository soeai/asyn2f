from asynfed.common.messages import MessageObject
from asynfed.common.messages.server.server_response_to_init import ExchangeAt


class ServerTrainingConfig(MessageObject):
    def __init__(self, strategy: str, exchange_at: dict, 
                 epoch_update_frequency: int = 1):
        self.strategy = strategy
        self.exchange_at = ExchangeAt(**exchange_at)
        self.epoch_update_frequency = epoch_update_frequency or 1