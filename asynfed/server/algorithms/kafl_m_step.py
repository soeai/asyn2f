
# # Standard library imports
# from threading import Thread, Lock
# from time import sleep
# import concurrent.futures
# import copy
# import logging
# import os
# import shutil
# import sys
# from typing import Dict

# # Third party imports
# from asynfed.common.config import MessageType
# from asynfed.common.messages import Message
# from asynfed.common.messages.client import ClientInitConnection, ClientModelUpdate, NotifyEvaluation, TesterRequestStop
# from asynfed.common.messages.server import ServerModelUpdate, PingToClient, ServerRequestStop
# from asynfed.common.messages.server.server_response_to_init import ServerRespondToInit, ModelInfo, StorageInfo
# import asynfed.common.messages as message_utils

# # Local imports
# from asynfed.server.objects import Worker
# from asynfed.server import Server


# thread_pool_ref = concurrent.futures.ThreadPoolExecutor
# lock = Lock()

# LOGGER = logging.getLogger(__name__)
# logging.getLogger("pika").setLevel(logging.WARNING)
# LOGGER.setLevel(logging.INFO)

# class KAFLMStepServer(Server):
#     def __init__(self, config: dict):
#        super().__init__(config)

#     def start(self):
#         self._start_threads()
        
#     # def _handle_when_receiving_message(self, message):
    