# -*- coding: utf-8 -*-
"""
Created on Wed Jan 25 2023

Anders Ryssdal and Victor Aasvær

Classes storing the system parameters used in the project
"""

#Object containing information about grid system
class System:
    def __init__(self):
        self.Nodes = {}                                     #Dict with all nodes in the system
        self.Lines = {}                                     #Dict with all lines in the system
        self.PTDFs = {}                                     #PTDF_ln
        self.DA_volumes = {}                                #P^(DA)_tn
        self.NetVolumes = {"DA":False, "Nodal":False,"Re-dispatch":False,"Pre zonal":False,"Post Zonal":False,}       #P^(DA)_tn, adjusted for model results
        
    #Function returning list with line object
    def getLineList(self,category): 
        List = []
        for l in self.Lines:
            if category == "All":
                List.append(l)
            elif category =="Flex" and self.Lines[l].isFlex == 1:
                List.append(l)
            elif category == "Not flex" and self.Lines[l].isFlex == 1 == 0:
                List.append(l)
        return List
    
    #Function returning list with node object
    def getNodeList(self, category):
        List = []
        for n in self.Nodes:
            if category == "All":
                List.append(n)
            elif category == "Flex" and self.Nodes[n].isFlex==1:
                List.append(n)
            elif category == "Not flex" and self.Nodes[n].isFlex==0:
                List.append(n)
        return List
    
    
    def to_dict(self):
        Dict = {}
        for name,value in vars(self).items():
            if name=="Nodes" or name=="Lines":
                Dict[name] = {ID:obj.to_dict() for ID,obj in value.items()}
            else:
                Dict[name] = value
        return Dict
    
    @classmethod
    def from_dict(cls,Dict):
        sys = cls()
        for name,value in vars(sys).items():
            if name == "Nodes": 
                setattr(sys,name, {ID:Node.from_dict(nodeDict) for ID,nodeDict in Dict[name].items()})
            elif name=="Lines":
                setattr(sys,name,{int(ID):Line.from_dict(lineDict) for ID,lineDict in Dict[name].items()})
            elif name=="NetVolumes":
                for m in Dict[name]:
                    if Dict[name][m]:
                        value[m] = {}
                        for j in Dict[name][m]:
                            value[m][int(j)] = Dict[name][m][j]
                    else:
                        value[m] = False
            else:
                for j in Dict[name]:
                    value[int(j)] = Dict[name][j]
        return sys
    
    
#Line class used as a container in the System class
class Line:        
    def __init__(self,ID,From,To,Type,Cap,Dist,b,x,r,c,isFlex, Cap_ka):
        self.ID = ID
        self.From = From
        self.To = To
        self.Type = Type
        self.Capacity = Cap
        self.Distance = Dist           
        self.b = b
        self.x_per_km = x
        self.r_per_km = r
        self.c_per_km = c
        self.isFlex = isFlex
        self.Capacity_ka = Cap_ka
    
    def to_dict(self):
        Dict = {}
        for name,value in vars(self).items():
            Dict[name] = value
        return Dict
    
    @classmethod
    def from_dict(cls,Dict):
        line = cls(Dict["ID"],Dict["From"],Dict["To"],Dict["Type"],Dict["Capacity"],Dict["Distance"],Dict["b"],Dict["x_per_km"],Dict["r_per_km"],Dict["c_per_km"],Dict["isFlex"],Dict["Capacity_ka"])
        return line
    
#Node class used as a container in the System class
class Node:        
    def __init__(self,ID,V,Type,geoData,zone,isFlex,isHost,loadShare):
        self.ID = ID
        self.Voltage = V
        self.type = Type
        self.geoData = geoData
        self.zone = zone
        self.isFlex = isFlex
        self.isHost = isHost
        self.loadShare = loadShare
        
    def to_dict(self):
        Dict = {}
        for name,value in vars(self).items():
            Dict[name] = value
        return Dict
    
    @classmethod
    def from_dict(cls,Dict):
        node = cls(Dict["ID"],Dict["Voltage"],Dict["type"],Dict["geoData"],Dict["zone"],Dict["isFlex"],Dict["isHost"],Dict["loadShare"])
        return node
    
        