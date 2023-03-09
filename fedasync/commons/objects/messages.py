

from abc import ABC, abstractmethod
import json


class Message(ABC):
    """
    This is the abstract class of Message objects.
    A message object will have the ability to convert it's properties into a dictionary.
    A message object can construct it's state from a dict as well.
    Any message will extend this class
    """
    
    def __init__(self, dict_object: dict = None) -> None:
        super().__init__()
        
        if dict_object != None:
            self.construct_from_json(dict_object)
            
    
    @abstractmethod
    def to_dict(self):
        """
        """
    
    @abstractmethod
    def construct_from_dict(self):
        """
        """
    
    def to_string(self):
        return json.dump(self.to_dict())
    
    
    
# implement from Message.
class GlobalMessage(Message):
    def __init__(self, dict_object: dict = None) -> None:
        super().__init__(dict_object)
        
    # Overidde methods ...