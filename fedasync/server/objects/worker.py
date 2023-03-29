from typing import List, Dict



class Worker:
    """
    - This is the Worker class that contains information of worker.
    - Add more properties to this class.
    """
    def __init__(self, id: str) -> None:
        
        # Properties
        self.id: str = id
        self.sys_info = {}
        self.data_desc = {}
        self.qod = {}
        self.current_version = 0
        self.performance = 0.0
        self.lost = 0.0
        self.n_update = 0

    def reset(self):
        """
        reset all properties 
        """

    def __str__(self):
        """
        Implement toString function here!
        """
    
    
    
    
    