from typing import List

class LabelMap:
    def __init__(self):
        self.map = {}
        self.map_bad = {}

    def add(self,label:str,id:str)->None:
        self.map[label] = id

    def add_bad(self,label:str,id:str)->None:
        self.map_bad[label] = id
    
    def add_mapping(self,og,grounded,mask)->None:
        for el in og:
            if  isinstance(og[el],List):
                for i,term in enumerate(og[el]):
                    if mask[el][i]:
                        self.add(term,grounded[el][i]['ID'])
                    else:
                        self.add_bad(term,grounded[el][i]['ID'])
            elif el !='id':
                if mask[el]:
                    self.add(og[el],grounded[el]['ID'])
                else:
                    self.add_bad(og[el],grounded[el]['ID'])

    def in_maps(self,el)->bool:
        return el in self.map or el in self.map_bad

    def check_past(self,sample:dict)->bool:
        run = False
        for el in sample:
            if  isinstance(sample[el],List):
                for term in sample[el]:
                    if not self.in_maps(term):
                        run = True
            elif el !='id':
                if not self.in_maps(sample[el]):
                    run = True
        return run