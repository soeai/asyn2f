import json
from typing import Optional, Dict, Union


class Message:
    """
    - This is a Message Object class that can convert dictionary object to its own pre-defined states
    easy for coding.
    - It can also convert its own states to a string that make easy for transferring the message.

    Follow the Single Responsibility principal that make the code easy to adapt with the changes later.

    To use this, you can create a class that extend (inherit) this class.
    inside the __init__ function should have a message that has dictionary type:
    class Example(Message):
        def __init__(self, message: dict):
            # define your attributes here.


            # in the end of this function, call the deserialize function that take the message ass input.
            # this will set all attribute of the Example class with the corresponding field in the message
            self.deserialize(message):


    """

    def deserialize(self, message: Union[str, Dict]) -> object:
        """
        @param message: is a string message taken from rabbitmq
        @return: return object itself
        """
        if message is not None:
            if type(message) is str:
                message = json.loads(message)

            # Iterate through keys in the input dictionary
            for key in message:
                # If the value associated with the key is not a dictionary,
                # set the attribute with the key and value
                if type(message[key]) != dict:
                    setattr(self, key, message[key])
                # If the value is a dictionary,
                # recursively call construct_msg on the dictionary
                # and set the attribute with the resulting object
                elif type(message[key]) == dict:
                    setattr(self, key, self.__dict__[key].deserialize(message[key]))

        # Return the deserialized object
        return self

    def __str__(self):
        return self.serialize()

    def serialize(self) -> str:

        # Create an empty dictionary to store the serialized object
        result: dict = {}
        # Iterate through the object's attributes
        for key in self.__dict__:
            # If the attribute is a basic data type (str, list, dict, int, tuple, set),
            # add it to the dictionary with its key
            if type(self.__dict__[key]) in [str, list, dict, int, tuple, set, float]:
                result[key] = self.__dict__[key]
            # If the attribute is an object, add its dictionary representation to the dictionary
            else:
                try:
                    result[key] = self.__dict__[key].__dict__
                except Exception as e:
                    print(e)
                    print(self.__dict__[key])


        # Return the dictionary as a JSON string
        return json.dumps(result)
