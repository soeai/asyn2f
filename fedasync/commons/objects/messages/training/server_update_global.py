

from ..messages import Message

class ServerUpdateGlobal(Message):
    def __init__(self, chosen_id: list, update_version: int, 
                 link: str) -> None:
        super().__init__({
            'chosen_id': chosen_id,
            'update_version': update_version,
            'link': link
        })
    
    # abstract method
    def to_dict(self) -> Dict:
        return {
            'chosen_id': self.chosen_id,
            'update_version': self.update_version,
            'link': self.link
        }
    
    # abstract method
    def construct_from_dict(self, dict_object: dict):
        self.chosen_id = dict_object['chosen_id']
        self.update_version = dict_object['update_version']
        self.link = dict_object['link']
