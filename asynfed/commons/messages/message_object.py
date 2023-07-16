from abc import ABC

class MessageObject(ABC):
    def to_dict(self):
        return {key: value if not isinstance(value, MessageObject) else value.to_dict() for key, value in self.__dict__.items()}