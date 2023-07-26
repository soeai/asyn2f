from asynfed.common.messages import MessageObject

# for stop message, just need the header
# nothing is included in the content for now
class ServerRequestStop(MessageObject):
    def __init__(self):
        pass
    