class PingToClient():
    def __init__(self, client_id):
        self.client_id = client_id

    def to_dict(self) -> dict:
        return self.__dict__

