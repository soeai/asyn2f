
from abc import ABC, abstractmethod
import json
from typing import Dict

class Message(ABC):
    """
    This is the abstract class of Message objects.
    A message object will have the ability to convert it's properties into a dictionary.
    A message object can construct it's state from a dict as well.
    Any message will extend this class
    """
    
    def __init__(self, dict_object: dict) -> None:
        super().__init__()
        # Set attribute from 
        for key in dict_object:
            setattr(self, key, dict_object[key])
            
    
    @abstractmethod
    def to_dict(self) -> Dict :
        return self.__dict__
    
    @abstractmethod
    def construct_from_dict(self, dict_object: dict):
        """
        """
    
    def to_string(self) -> str:
        return json.dumps(self.to_dict())
