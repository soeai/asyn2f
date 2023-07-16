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
    @classmethod
    def deserialize(cls, json_str):
        return json.loads(json_str)
    @classmethod
    def print_message(cls, dict_to_print):
        def check_value(value):
            if isinstance(value, bool):
                return 'True' if value else 'False'
            elif value is None:
                return 'None'
            elif isinstance(value, dict):
                return json.dumps(value)
            else:
                return value if value != '' else 'None'
        def print_dict(dict_to_print, offset=0):
            for k, v in dict_to_print.items():
                if isinstance(v, dict):
                    logging.info('|' + ' '*offset + f'{k:<20}' + ' '*(MAX_LENGTH-offset-20))
                    print_dict(v, offset=offset+OFFSET)
                else:
                    logging.info('|' + ' '*offset + f'{k:<20}: {check_value(v):<50}')

        MAX_LENGTH = 80
        OFFSET = 3
        logging.info('|' + '-'*MAX_LENGTH + '|')
        print_dict(dict_to_print)
        logging.info('|' + '-'*MAX_LENGTH + '|')
