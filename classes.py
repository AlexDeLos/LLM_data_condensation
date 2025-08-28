
class LabelMap:
    def __init__(self):
        self.map = {}

    def add_mapping(self,label:str,id:str):
        self.map[label] = id