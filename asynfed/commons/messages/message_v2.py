import json


class MessageV2:
    '''
    MessageV2 class is used to create a message object that can be sent to the server.
    params:
        message_type: str
        content: dict
        headers: dict

    Sample params:
        message_type: "init_connection"
        content: ClientInitConnection(),
        headers: {"session_id": "session_1", "client_id": "client_1""}
    '''
    def __init__(self, message_type, content=None, headers=None):
        self.message_type = message_type
        self.content = content.__dict__ or {}
        self.headers = headers or {}

    def to_json(self):
        to_dict = {
            "message_type": self.message_type,
            "content": self.content,
            "headers": self.headers
        }
        return json.dumps(to_dict)

    @classmethod
    def serialize(cls, dict_str):
        if ': false' in dict_str:
            dict_str = dict_str.replace(': false', ': False')
        if ': true' in dict_str:
            dict_str = dict_str.replace(': true', ': True')
        return eval(dict_str)


if __name__ == '__main__':
    temp_str = "{'asd': 'asdasd', '123': 44, 'bool': false}"
    msg = MessageV2.serialize(temp_str)
    print(msg)
    print(type(msg))
