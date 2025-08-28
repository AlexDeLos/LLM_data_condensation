from typing import List, Optional
import json

def load_json(path:str):
    with open(path, 'r') as file:
        object = json.load(file)
    return object


class LabelMap:
    def __init__(self, path:Optional[str]=None):
        self.path = path
        if path is None:
            self.map_good = {}
            self.map_bad = {}
            self.map = {}
        else:
            try:
                self.map_good = load_json(path+'/map_good.json')
                self.map_bad = load_json(path+'/map_bad.json')
                self.map = load_json(path+'/map.json')
            except:
                Warning('Path not found')
                self.map_good = {}
                self.map_bad = {}
                self.map = {}

    def add(self,label:str,id:str)->None:
        self.map[label] = id

    def add_good(self,label:str,id:str)->None:
        self.map_good[label] = id

    def add_bad(self,label:str,id:str)->None:
        self.map_bad[label] = id
    
    def add_mapping(self,og,grounded,mask)->None:
        for el in og:
            if  isinstance(og[el],List):
                for i,term in enumerate(og[el]):
                    if mask[el][i]:
                        self.add_good(term,grounded[el][i]['uniq_id'])
                    else:
                        self.add_bad(term,grounded[el][i]['uniq_id'])
            elif not (el =='id' or el == 'medium'):
                if mask[el]:
                    self.add_good(og[el],grounded[el]['uniq_id'])
                else:
                    self.add_bad(og[el],grounded[el]['uniq_id'])

    def in_maps_evaluated(self,el)->bool:
        return el in self.map_good or el in self.map_bad

    def in_maps(self,el)->bool:
        return self.in_maps_evaluated(el) or el in self.map
    

    def check_past(self,sample:dict)->bool:
        run = False
        for el in sample:
            if  isinstance(sample[el],List):
                for term in sample[el]:
                    if not self.in_maps_evaluated(term):
                        run = True
            elif el !='id':
                if not self.in_maps_evaluated(sample[el]):
                    run = True
        return run
    
    def save_map(self) -> None:
        with open(f'{self.path}/map_good.json', 'w') as handle:
            json.dump(self.map_good, handle)
        with open(f'{self.path}/map_bad.json', 'w') as handle:
            json.dump(self.map_bad, handle)
        with open(f'{self.path}/map.json', 'w') as handle:
            json.dump(self.map, handle)