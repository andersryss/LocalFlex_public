"""
Created on Sun Nov 27 2022

Victor and Anders

Results from flexibility models
"""
import pyomo.environ as pyo
import pandas as pd
import seaborn 
import collections
import math
import matplotlib.pyplot as plt
from Flex_supportFunctions import LoadFlow
from Flex_Bids import Bids
from Flex_Zones import Zones



class Result:
    def __init__(self):
        self.read = {"Nodal":False,"Zonal":False,"Re-dispatch":False,"Post zonal":False}           #Show if base data has been read for the various models
        
        #Dicts representing the variables in the models 
        self.clearedUp = {"Nodal":{},"Zonal":{},"Re-dispatch":{},"Pre zonal":{},"Post zonal":{}}
        self.clearedDown = {"Nodal":{},"Zonal":{},"Re-dispatch":{},"Pre zonal":{},"Post zonal":{}}
        self.flow = {"Day ahead":{},"Nodal":{},"Re-dispatch":{},"Pre zonal":{},"Post zonal":{}}
        self.prod = {"Nodal":{},"Re-dispatch":{},"Pre zonal":{},"Post zonal":{}}
        self.charge = {"Nodal":{},"Pre zonal":{},}
        self.cost = {"Nodal": 0,"Zonal": 0, "Re-dispatch": 0,"Pre zonal":0,"Post zonal": 0}
        self.duals = {"Nodal":{},"Re-dispatch":{},"Pre zonal":{},"Post zonal":{}}

        
        #Data sorted and presented
        self.DataFrames = {}                    #All data that is stored as dataframes will be found here
    
    #Method converting object to a dictionary
    def to_dict(self):
        Dict = {}
        for name,value in vars(self).items():
            if name =="DataFrames":
                continue
            elif name == "bids" or name == "zones":    
                Dict[name] = value.to_dict()
            else:
                Dict[name] = value
        return Dict
 
    @classmethod
    def from_dict(cls,Dict):
        res = cls()
        for name,value in vars(res).items():
            if name == "DataFrames" or name not in Dict or name=="bids" or name=="zones":
                continue    
            elif name=="read" or name=="cost":
                setattr(res,name,Dict[name])
                continue
            for m in Dict[name]:
                if name=="flow":
                    for t in Dict[name][m]:
                        value[m][int(t)] = {}
                        for l in Dict[name][m][t]:
                            value[m][int(t)][int(l)] = Dict[name][m][t][l]
                elif name=="charge":
                    for t in Dict[name][m]: 
                        value[m][int(t)] = {}
                        for i in Dict[name][m][t]:
                            value[m][int(t)][int(i)] = Dict[name][m][t][i]
                else: 
                    for t in Dict[name][m]:
                        value[m][int(t)] = Dict[name][m][t]


        return res
    
    #%%Functions reading base data from the models
    def read_nodal(self,model,Data):
        self.cost["Nodal"] += pyo.value(model.obj)
        
        #Get flow
        flow = LoadFlow(Data)
        for t in model.Periods:
            self.clearedUp["Nodal"][t] = {}
            self.clearedDown["Nodal"][t] = {}
            self.flow["Nodal"][t] = {}
            self.flow["Day ahead"][t] = {}
            self.prod["Nodal"][t] = {}
            self.charge["Nodal"][t] = {}
            self.duals['Nodal'][t] = {}
            
            #upBids
            for b in Data.Bids.upBids:
                self.clearedUp["Nodal"][t][b] = pyo.value(model.clearedUp[b,t])
            #downBids
            for b in Data.Bids.downBids:
                self.clearedDown["Nodal"][t][b] = pyo.value(model.clearedDown[b,t])
            #Flow
            for l in Data.System.getLineList("All"):
                self.flow["Nodal"][t][l] = pyo.value(model.flow[l,t])
                self.flow["Day ahead"][t][l] = flow[t][l]
            #Prod
            for n in Data.System.getNodeList("All"):
                self.prod["Nodal"][t][n] = pyo.value(model.prod[n,t])
                self.duals['Nodal'][t][n] = model.dual[model.netProduction_cons[n,t]]
            #Charge
            for i in Data.Participants.types["Battery"]:
                self.charge["Nodal"][t][i] = pyo.value(model.charge[i,t])
        
        self.read["Nodal"] = True
                    
        
    def read_zonal(self,model,Data):
        for t in model.Periods:
            self.clearedUp["Pre zonal"][t] = {}
            self.clearedUp["Zonal"][t] = {}
            self.clearedDown["Pre zonal"][t] = {}
            self.clearedDown["Zonal"][t] = {}
            self.flow["Pre zonal"][t] = {}
            self.prod["Pre zonal"][t] = {}
            self.charge["Pre zonal"][t] = {}
            self.duals["Pre zonal"][t] = {}
    
            #upBids
            for b in Data.Bids.upBids:
                if Data.Bids[b].Participant != "Re-dispatch":
                    self.clearedUp["Pre zonal"][t][b] = pyo.value(model.clearedUp[b,t])
                    self.cost["Pre zonal"] += self.clearedUp["Pre zonal"][t][b] * Data.Bids[b].Price[t]
                    self.clearedUp["Zonal"][t][b] = pyo.value(model.clearedUp[b,t])
                    self.cost["Zonal"] += self.clearedUp["Zonal"][t][b] * Data.Bids[b].Price[t]
            #downBids
            for b in Data.Bids.downBids:
                if Data.Bids[b].Participant != "Re-dispatch":
                    self.clearedDown["Pre zonal"][t][b] = pyo.value(model.clearedDown[b,t])           
                    self.cost["Pre zonal"] += self.clearedDown["Pre zonal"][t][b] * Data.Bids[b].Price[t]
                    self.clearedDown["Zonal"][t][b] = pyo.value(model.clearedDown[b,t])           
                    self.cost["Zonal"] += self.clearedDown["Zonal"][t][b] * Data.Bids[b].Price[t]
            #Flow
            lines = Data.Zones.cutLines[t] 
            for l in lines:
                self.flow["Pre zonal"][t][l] = pyo.value(model.flow[l,t])
            #Prod
            for z in Data.Zones.nodes[t]:
                self.prod["Pre zonal"][t][z] = pyo.value(model.prod[z,t])
                self.duals["Pre zonal"][t][z] = model.dual[model.netProduction_cons[z, t]]
            #Charge
            for i in Data.Participants.types["Battery"]:
                self.charge["Pre zonal"][t][i] = pyo.value(model.charge[i,t])
        
        self.read["Zonal"] = True
    
    
    def read_re(self,model,Data):
        self.cost["Re-dispatch"] += pyo.value(model.obj)
        for t in model.Periods:
            self.clearedUp["Re-dispatch"][t] = {}
            self.clearedDown["Re-dispatch"][t] = {}
            self.flow["Re-dispatch"][t] = {}
            self.prod["Re-dispatch"][t] = {}
            self.duals['Re-dispatch'][t] = {}
            
            #upBids
            for b in Data.Bids.upBids:
                if Data.Bids[b].Participant == "Re-dispatch":
                    self.clearedUp["Re-dispatch"][t][b] = pyo.value(model.clearedUp[b,t])
            #downBids
            for b in Data.Bids.downBids:
                if Data.Bids[b].Participant == "Re-dispatch":
                    self.clearedDown["Re-dispatch"][t][b] = pyo.value(model.clearedDown[b,t])
                
            #Flow
            for l in Data.System.getLineList("All"):
                self.flow["Re-dispatch"][t][l] = pyo.value(model.flow[l,t])
            #Prod
            for n in Data.System.getNodeList("All"):
                self.prod["Re-dispatch"][t][n] = pyo.value(model.prod[n,t])
                self.duals['Re-dispatch'][t][n] = model.dual[model.netProduction_cons[n, t]]
                      
        self.read["Re-dispatch"] = True
    
    def read_postZonal(self,model,Data):
        self.cost["Post zonal"] += pyo.value(model.obj)
        self.cost["Zonal"] += pyo.value(model.obj)
        for t in model.Periods:
            self.clearedUp["Post zonal"][t] = {}
            self.clearedDown["Post zonal"][t] = {}
            self.flow["Post zonal"][t] = {}
            self.prod["Post zonal"][t] = {}
            self.duals['Post zonal'][t] = {}
            
            
            #upBids
            for b in Data.Bids.upBids:
                if Data.Bids[b].Participant == "Re-dispatch":
                    self.clearedUp["Post zonal"][t][b] = pyo.value(model.clearedUp[b,t])
                    self.clearedUp["Zonal"][t][b] = pyo.value(model.clearedUp[b,t])
            #downBids
            for b in Data.Bids.downBids:
                if Data.Bids[b].Participant == "Re-dispatch":
                    self.clearedDown["Post zonal"][t][b] = pyo.value(model.clearedDown[b,t])
                    self.clearedDown["Zonal"][t][b] = pyo.value(model.clearedDown[b,t])
            #Flow
            for l in Data.System.getLineList("All"):
                self.flow["Post zonal"][t][l] = pyo.value(model.flow[l,t])
            #Prod
            for n in Data.System.getNodeList("All"):
                self.prod["Post zonal"][t][n] = pyo.value(model.prod[n,t])
                self.duals['Post zonal'][t][n] = model.dual[model.netProduction_cons[n, t]]
        
        self.read["Post zonal"] = True
        

#Function that runs all functions interpreting the results
def interpretResult(Result,data):
    
    FindFlows(Result,data,"Between zones")      #Flows between zones
    FindFlows(Result,data,"Flexibility lines")  #Flows in all flex lines
    FindFlows(Result,data,"All lines")          #Flows in all lines
    FindCosts(Result,data)                      #Costs for each model


#%% Reading the line flows into dataframes 
def FindFlows(Result,Data,Filter):

    dataframes = {t:0 for t in Result.flow["Day ahead"]} 
    for t in Result.flow["Day ahead"]:
        output = {"Line":[],"From":[],"To":[],"Capacity":[],"Flexibility area":[],"Between zones":[],"Day ahead":[],"Nodal flow":[],"Zonal flow":[],"Re-dispatch flow":[],"Post zonal flow":[]}
        zoneLines = list(Result.flow["Pre zonal"][t].keys())

        flexLines = Data.System.getLineList("Flex")
        
        if Filter == "Between zones":
            lines = zoneLines
            del output["Between zones"]
            del output["Flexibility area"]
        elif Filter == "Flexibility lines":
            lines = flexLines
            del output["Flexibility area"]         
        elif Filter == "All lines":
            lines = Data.System.getLineList("All")
        
        for l in lines:
            line = Data.System.Lines[l]
            
            output["Line"].append("Line {}".format(line.ID))
            output["From"].append(line.From)
            output["To"].append(line.To)
            output["Capacity"].append(line.Capacity)
            output["Day ahead"].append(Result.flow["Day ahead"][t][l]) 
            output["Nodal flow"].append(Result.flow["Nodal"][t][l])
            output["Re-dispatch flow"].append(Result.flow["Re-dispatch"][t][l])
            output["Post zonal flow"].append(Result.flow["Post zonal"][t][l])
            
            if Filter == "Between zones":
                output["Zonal flow"].append(Result.flow["Pre zonal"][t][l])
                
            elif l in zoneLines:
                output["Zonal flow"].append(Result.flow["Pre zonal"][t][l])
                output["Between zones"].append(1)
                if Filter =="All lines" and l in flexLines:
                    output["Flexibility area"].append(1)
                elif Filter =="All lines":
                    output["Flexibility area"].append(0)
            else:
                output["Zonal flow"].append(None)
                output["Between zones"].append(0)
                if Filter =="All lines" and l in flexLines:
                    output["Flexibility area"].append(1)
                elif Filter =="All lines":
                    output["Flexibility area"].append(0)
        dataframes[t] = pd.DataFrame(output).set_index("Line")
    Result.DataFrames["Flow: " + Filter] = dataframes

#%%Create dataframe showing costs for the various models, per period  
def FindCosts(Result,data):
    DFs = {"Hourly cost (FA)":pd.DataFrame(),"Hourly cost (TA)":pd.DataFrame(),"Daily cost (FA)":pd.DataFrame(),"Daily cost (TA)":pd.DataFrame()}

    for s in Result.read:
        costLists = {"Hourly cost (FA)":{},"Hourly cost (TA)":{},"Daily cost (FA)":collections.defaultdict(int),"Daily cost (TA)":collections.defaultdict(int)}
        for t in Result.flow["Day ahead"]:
            costs= {"Flex":0,"All":0}
            for b in Result.clearedUp[s][t]:
                costs["All"] += data.Bids[b].Price[t] * Result.clearedUp[s][t][b]
                if data.System.Nodes[data.Bids[b].Node].isFlex:
                    costs["Flex"] += data.Bids[b].Price[t] * Result.clearedUp[s][t][b]
            for b in Result.clearedDown[s][t]:
                costs["All"] += data.Bids[b].Price[t] * Result.clearedDown[s][t][b]
                if data.System.Nodes[data.Bids[b].Node].isFlex:
                     costs["Flex"] += data.Bids[b].Price[t] * Result.clearedDown[s][t][b]
            costLists["Hourly cost (FA)"]["t={}".format(t)] = costs["Flex"]
            costLists["Hourly cost (TA)"]["t={}".format(t)] = costs["All"]
            
            day = math.floor((t-1)/24)
            costLists["Daily cost (FA)"]["d={}".format(day)] += costs["Flex"]
            costLists["Daily cost (TA)"]["d={}".format(day)] += costs["All"]
            
        for c in costLists:
            res = {"Model":s,"Total":sum(costLists[c].values())}
            res.update({key:val for key,val in costLists[c].items()})
            DFs[c]=pd.concat([DFs[c],pd.Series(res).to_frame().T,],ignore_index=True)
      

    for c in DFs:
        DFs[c] = DFs[c].set_index("Model")  
        Result.DataFrames[c] = DFs[c]
    
    return DFs



    