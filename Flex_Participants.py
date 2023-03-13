"""
Created on Wed Jan 25 2023

Anders Ryssdal and Victor Aasvær

Classes storing the Participants used in the project
"""
import collections

#Object containing all market participants, including lookup dictionaries
class Participants:
    def __init__(self):
        self.fullDict = dict()                                      #All participants
        self.types = collections.defaultdict(list)                  #The participant types as keys and values are lists of corresponding participant IDs
        self.nodes = collections.defaultdict(list)                  #The nodes are keys and the values are lists of corresponding participant IDs
   
        self.batteryEfficiency = {"Charge":1,"Discharge":1}         #n^+ and n^-
    
    def __getitem__(self, ID):
        return self.fullDict[ID]
    
    def to_dict(self):
        Dict = {}
        for ID,participant in self.fullDict.items():
            Dict[ID] = participant.to_dict()
        return Dict
    
    @classmethod
    def from_dict(cls,Dict):
        collection = cls()
        for ID,subDict in Dict.items():
            participant = Participant.from_dict(subDict)
            collection.fullDict[int(ID)] = participant
            collection.types[participant.Type].append(participant.ID)
            collection.nodes[participant.Node].append(participant.ID)
        return collection



class Participant:
    def __init__(self,ID,Type,Node,Size,costScaling):
        self.ID = ID
        self.Type = Type
        self.Node = Node
        self.Size = Size
        self.costScaling = costScaling
    
    def to_dict(self):
        Dict = {}
        for name,value in vars(self).items():
            Dict[name] = value
        return Dict
    
    @classmethod
    def from_dict(cls,Dict):
        return cls(Dict["ID"],Dict["Type"],Dict["Node"],Dict["Size"],Dict["costScaling"])
