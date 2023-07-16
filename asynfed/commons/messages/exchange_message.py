import logging
import json

class Message:      
    '''
    Message class is used to create a message object that can be sent to the server.
    params:
        content: dict
        headers: dict
    Sample params:
        headers: {
            "timestamp": "2021-01-01 00:00:00"
            "message_type": "init_connection",
            "session_id": "session_1", 
            "client_id": "client_1"
        }
        content: {
        }
    '''

    def __init__(self, headers: dict = {}, content: dict = {}):
        self.headers = headers
        self.content = content

    def to_json(self):
        dict_object = {
            "headers": self.headers,
            "content": self.content,
        }
        return json.dumps(dict_object)
    
