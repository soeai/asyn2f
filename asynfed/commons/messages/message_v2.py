import json


class MessageV2:
    '''
    MessageV2 class is used to create a message object that can be sent to the server.
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
    def __init__(self, content=None, headers=None):
        self.headers = headers or {}
        self.content = content.__dict__ or {}

    def to_json(self):
        to_dict = {
            "headers": self.headers,
            "content": self.content,
        }
        return json.dumps(to_dict)

    @classmethod
    def serialize(cls, dict_str):
        if ': false' in dict_str:
            dict_str = dict_str.replace(': false', ': False')
        if ': true' in dict_str:
            dict_str = dict_str.replace(': true', ': True')
        if ': null' in dict_str:
            dict_str = dict_str.replace(': null', ': None')
        return eval(dict_str)

    @classmethod
    def print_message(cls, dict_to_print):
        def check_value(value):
            if type(value) is bool:
                v = 'True' if value else 'False'
                return v
            if value is None:
                return 'None'
            return value or ''
        MAX_LENGTH = 80
        OFFSET = 3
        print('|' + '-'*MAX_LENGTH + '|')
        for k, v in dict_to_print.items():
            if type(v) is dict:
                print(f'|{k:<20}' + ' '*(MAX_LENGTH-20) )
                for k2, v2 in v.items():
                    if type(v2) is dict:
                        print('|' + ' '*OFFSET + f'{k2:<20}' + ' '*(MAX_LENGTH-OFFSET-20))
                        for k3, v3 in v2.items():
                            print('|'+  ' '*OFFSET*2 + f'{k3:<20}: {check_value(v3):<50}' )
                    else:
                        print('|' + ' '*OFFSET + f'{k2:<20}: {v2:<50}' )
            elif type(v) is bool:
                v = 'True' if v else 'False'
                print('|' + ' '*OFFSET + f'{k:<20}: {v:<50}' )
            else:
                if len(v) == 0:
                    v = 'None'
                print('|' + ' '*OFFSET + f'{k:<20}: {v:<50}') 
        print('|' + '-'*MAX_LENGTH + '|')


if __name__ == '__main__':
    temp_str = "{'asd': 'asdasd', '123': 44, 'bool': false}"
    msg = MessageV2.serialize(temp_str)
    print(msg)
    print(type(msg))
