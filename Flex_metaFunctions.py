"""
Created on Thu Oct 14 2022

Anders Ryssdal and Victor Aasvær

Functions used to execute the total model system
"""
from Flex_data import Data
from Flex_supportFunctions import Save,Load,HiddenPrints,timeString
from Flex_nodeClearing import NodeClearing
from Flex_zoneClearing import ZoneClearing
from Flex_redispatch import Redispatch,Redispatch_post
from Flex_Result import Result,interpretResult

import time
import os
import copy

#%%Support functions

#Function loading result objects that have been stored in the correct way
def loadResults(runID):
    results = {}
    data= Load(Data,"Data_{}".format(runID),folder=["Results"])
        
    for root, dirs, files in os.walk(os.getcwd()+"\\Results",topdown=False):
        folder = root.rsplit("\\",1)[-1]
        if  folder != "Results" and "_{}".format(runID) not in folder:
            results[folder] = {} 
            for name in files:
                if "_{}".format(runID) in name:
                    results[folder][name] = Load(Result,name,folder=["Results",folder])
                    interpretResult(results[folder][name],data)
            for name in dirs:
                if "_{}".format(runID) in name:
                    results[folder][name] = Load(Result,name,folder=["Results",folder])
                    interpretResult(results[folder][name],data)
    return results,data

def runModels(res,data,penalty=50):
    for day in range(1,data.days+1):    
        dayTime = time.time()
        print("\t\tRunning models for day {}".format(day))
        with HiddenPrints():
            NodeClearing(data,res,day)
            Redispatch(data,res,day)
            ZoneClearing(data,res,day,penalty)
            Redispatch_post(data,res,day)
        print("\t\tFinished modelling day {} after {}".format(day,timeString(time.time()-dayTime)))

#Function running the main analysis, in addition to all the sensitivities. Store the results with an ID
def runAll(runID,data=False,days = 14):
    if not data:
        data = Data.create(days)
    
     
    results = dict()
    
    #Run the base cases and sensitivities
    results["Ordinary results"] = ordinaryRun(data,runID)
    results["Redispatch sensitivity"] = RedispatchSensitivity(data,runID)
    results["nZones sensitivity"] = nZonesSensitivity(data,runID)
    results["Flexibility cost sensitivity"] = flexCostSensitivity(data,runID)
    results["Flexibility volume sensitivity"] = flexVolSensitivity(data,runID)
    results["Line capacity sensitivity"] = lineCapSensitivity(data,runID)
    results["No TS cap"] = noTScapRun(data,runID)

    
    return results,data
    
        


        
#%% Run all 14 days
def ordinaryRun(data,runID):
    print("Ordinary run")
    res = Result()
     
    modelTime = time.time()      
    
    runModels(res,data, penalty=50)        
    print("\tFinished running models after {}\n".format(timeString(time.time()-modelTime)))
                             
    
    interpretResult(res,data)
    
    return res
        

#%%   Change both redispatch costs and the penalty in the zonal model
def RedispatchSensitivity(Data,runID,costs=[30,40,60,70],days=5):
    print("Running re-dispatch sensitvity")
    mainTime=time.time()
    data = copy.deepcopy(Data)
    data.days = days
    results = {}
    #Iterate over each cost scenario
    for c in costs:
        print(f"\tRe-dispatch cost of {c}:")
        for b in data.Bids.participantBids["Re-dispatch"]:
            data.Bids[b].changePrice(c)
        
        res = Result()
        modelTime = time.time()
        with HiddenPrints(): 
            runModels(res,data,c)                          
        print("\tFinished running models after {}\n".format(timeString(time.time()-modelTime)))
        
       
        interpretResult(res,data)
        results["reCost={}".format(c)] = res
                
    print("\tTotal time spent is {}".format(round(time.time()-mainTime)))
    
    return results
    
#%% 
def nZonesSensitivity(Data,runID,saving,nZonesList=[3,7,10,15,30],days=5):
    print("Running nZones sensitivity")
    mainTime=time.time()
    

    data = copy.deepcopy(Data)
    data.days = days
    results = {}
    #Iterate over each scenario of nZones
    for nZones in nZonesList:
        partitioningTime = time.time()
        
        #New zone partitioning
        with HiddenPrints():
            data.runZonePartitioning(nZones,5)
            data.fill_ZPTDFs()
        
        print("\tFinished altering zone data after {}".format(timeString(time.time()-partitioningTime)))

        res = Result()
        
        modelTime = time.time()
        runModels(res,data)       
        print("\tFinished running models after {}".format(timeString(time.time()-modelTime)))   
        

        interpretResult(res,data)
        results["nZones={}".format(nZones)] = res
            
    

    print("\tTotal time spent is {}".format(round(time.time()-mainTime)))
        
    return results  
    

#%% 
def flexCostSensitivity(Data,runID,saving,costs=[0.5,0.75,1.25,1.5],days=5):
    print("Running flexibility cost sensitivity")
    mainTime=time.time()

    #Create and initialize data object
    data = copy.deepcopy(Data)
    data.days = days
    results = {}
    
    #Iterate over each cost scenario
    for c in costs:
        print("\tFlexibility cost scaling of {}%".format(c*100))
        data.Bids = copy.deepcopy(Data.Bids)
        #Change bid costs
        for ID,bid in data.Bids.fullDict.items():
            if bid.Participant != "Re-dispatch":
                bid.scalePrice(c) 
        
        
        # Result object
        res = Result()
        
        modelTime=time.time()
        runModels(res,data)       
        
        print("\tFinished running models after {}".format(timeString(time.time()-modelTime)))
        
        interpretResult(res,data)
        results["Cost scaling={}".format(c)]= res                    

        
    print("\tTotal time spent is {}".format(round(time.time()-mainTime)))
     
    
    return results

#%%   
def flexVolSensitivity(Data,runID,saving,volumes=[0.5,2,4,10,15],days=5):
    print("Running flexibility volume sensitivity" )
    mainTime=time.time()

    #Create and initialize data object
    data = copy.deepcopy(Data)
    data.days = days
    
    results = {}


    #Iterate over each cost scenario
    for v in volumes: 
        print("\tVolume scaled by {}".format(v))
        data.Bids = copy.deepcopy(Data.Bids)
        #Change bid volumes
        for ID,bid in data.Bids.fullDict.items():
            if bid.Participant != "Re-dispatch": 
                bid.scaleVolume(v)

        res = Result()
        
        modelTime=time.time()
        runModels(res,data)       
        
        print("\tFinished running models after {}".format(timeString(time.time()-modelTime)))
        
        interpretResult(res,data)
        results["Volume scaling={}".format(v)] = res                    
 
       
    print("\tTotal time spent is {}".format(round(time.time()-mainTime)))
     

    return results

#%%   
def lineCapSensitivity(Data,runID,saving,scaling=[1.15,1.3,1.5],days=5):
    print("Running line capacity sensitivity")
    mainTime=time.time()

    #Create and initialize data object
    data = copy.deepcopy(Data)
    data.days = days
    results = {}

    
    #Iterate over each cost scenario
    for s in scaling:   
        print("\tCapacity scaled by {}".format(s))
        data.System = copy.deepcopy(Data.System)
        for line in data.System.Lines:
            data.System.Lines[line].Capacity = data.System.Lines[line].Capacity * s

        # Result object
        res = Result()
        
        modelTime=time.time()
        runModels(res,data)       
        
        print("\tFinished running models after {}".format(timeString(time.time()-modelTime)))
        
        interpretResult(res,data)
        results["Capacity scaling={}".format(s)]= res                    
 

    print("\tTotal time spent is {}".format(round(time.time()-mainTime)))
     

    return results
#%% 
def noTScapRun(Data,runID,saving,days=5):
    print("Running sensitivity where TS line capacities are removed ")
    data=copy.deepcopy(Data)
    data.days = days
    for ID,line in data.System.Lines.items():
        if "R_" not in line.To and "R_" not in line.From:
            line.Capacity = float('inf')
    # Result object
    res = Result()
    
    modelTime=time.time()
    
    runModels(res,data)        
    
    print("\tFinished running models after {}\n".format(timeString(time.time()-modelTime)))
                      
    interpretResult(res,data)
     
    return res
        