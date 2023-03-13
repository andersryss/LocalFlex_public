"""
Created on Thu Oct 20 2022

Anders Ryssdal and Victor Aasvær

Node clearing model
"""
import pyomo.environ as pyo
import time
import copy
from Flex_supportFunctions import timeString

def Redispatch(Data,Result,day,Context="Ordinary"):
    #Tracking running time
    startTime = time.time()
    print("Initilalizing Re-dispatch")
    
    #Create the model object
    model = pyo.ConcreteModel()
    
    #%% Model sets  
    model.Periods = pyo.Set(initialize = list(range((day-1)*24+1,day*24+1)))                                                      #T
    model.Nodes = pyo.Set(initialize=Data.System.getNodeList("All"))                                        #N
    model.Lines = pyo.Set(initialize = Data.System.getLineList("All"))                                      #L

    def upBids(model):
        for b in Data.Bids.upBids:
            if Data.Bids[b].Participant == "Re-dispatch":
                yield b
    model.upBids = pyo.Set(initialize=upBids)
    
    def downBids(model):
        for b in Data.Bids.downBids:
            if Data.Bids[b].Participant == "Re-dispatch":
                yield b
    model.downBids = pyo.Set(initialize=downBids)

    #%%Model variables
    model.clearedUp = pyo.Var(model.upBids,model.Periods,within=pyo.NonNegativeReals)                                         
    model.clearedDown = pyo.Var(model.downBids,model.Periods,within=pyo.NonNegativeReals)                                             
    model.flow = pyo.Var(model.Lines,model.Periods)
    model.prod = pyo.Var(model.Nodes,model.Periods)

    
    #%%Objective function
    def ObjFunc(model):
        return sum(model.clearedUp[b,t]*Data.Bids[b].Price[t] for b in model.upBids for t in model.Periods ) + sum(model.clearedDown[b,t]*Data.Bids[b].Price[t]  for b in model.downBids for t in model.Periods )
    model.obj = pyo.Objective(rule=ObjFunc,sense=pyo.minimize)
    
    
    #%% Model constraints
    
    #b: The market must keep the energy balance
    def marketBalance_rule(model,t):
        return sum(model.clearedUp[b,t] for b in model.upBids) - sum(model.clearedDown[b,t] for b in model.downBids) == 0
    model.marketBalance_cons = pyo.Constraint(model.Periods,rule=marketBalance_rule)
    
    
    #c: Find net production in each node
    def netProduction_rule(model,n,t):
        if Context == 'Post zonal':
            return  Data.System.NetVolumes["Zonal"][t][n] + sum(model.clearedUp[b,t] for b in Data.Bids.nodeBids[n] if b in model.upBids) - sum(model.clearedDown[b,t] for b in Data.Bids.nodeBids[n] if b in model.downBids) == model.prod[n,t]
        else:
            return  Data.System.DA_volumes[t][n]["Net"] + sum(model.clearedUp[b,t] for b in Data.Bids.nodeBids[n] if b in model.upBids) - sum(model.clearedDown[b,t] for b in Data.Bids.nodeBids[n] if b in model.downBids) == model.prod[n,t]
    model.netProduction_cons = pyo.Constraint(model.Nodes,model.Periods,rule=netProduction_rule)
    
    #d: Bid sizes restrict the clearing
    def bidSizes_rule1(model,b,t):
        return model.clearedUp[b,t] <= Data.Bids[b].Volume[t]
    model.bidSizes_cons1 = pyo.Constraint(model.upBids,model.Periods,rule=bidSizes_rule1)
    
    def bidSizes_rule2(model,b,t):
        return model.clearedDown[b,t] <= Data.Bids[b].Volume[t]
    model.bidSizes_cons2 = pyo.Constraint(model.downBids,model.Periods,rule=bidSizes_rule2)

    #e: Find line flow
    def lineFlow_rule(model,l, t):
        return model.flow[l,t] == sum(Data.System.PTDFs[l][n]*model.prod[n,t] for n in model.Nodes)
    model.lineFlow_cons = pyo.Constraint(model.Lines, model.Periods, rule=lineFlow_rule) 
    
    #f: Line capacity
    def lineCap_rule_1(model,l,t):
        return model.flow[l,t] <= Data.System.Lines[l].Capacity 
    model.lineCap_cons_1 = pyo.Constraint(model.Lines,model.Periods,rule=lineCap_rule_1)
    
    def lineCap_rule_2(model,l,t):
        return -model.flow[l,t] <= Data.System.Lines[l].Capacity 
    model.lineCap_cons_2 = pyo.Constraint(model.Lines,model.Periods,rule=lineCap_rule_2)
    
    print("Initilialize finished after {} \n".format(timeString(time.time()-startTime)))

        
        
    #%% Solving the problem
    startTime =time.time()
    print("Running Re-dispatch")
    
    #Deciding the solver
    model.dual = pyo.Suffix(direction = pyo.Suffix.IMPORT_EXPORT)
    opt = pyo.SolverFactory("gurobi")
    result=opt.solve(model,tee=False)

        
    print("Model run finished after {} \n".format(timeString(time.time()-startTime)))
    
    if Context == "Ordinary":
        Result.read_re(model,Data)
    elif Context == "Post zonal":
        Result.read_postZonal(model,Data)



#%%Function adapting data object to the zonal solution and doing redispatch, not accounting for redispatch bids accepted in zonal model
def Redispatch_post(Data,Result,day):

    
    DA_adjusted = {t:{n:Data.System.DA_volumes[t][n]["Net"] for n in Data.System.getNodeList("All")} for t in Data.Periods}
    
    for t in list(range((day-1)*24+1,day*24+1)):
        #Adjusting DA volumes inside of the flexibility area, but do not use the redispatch bids
        for b in Data.Bids.upBids:
            if Data.Bids[b].Participant != "Re-dispatch":
                DA_adjusted[t][Data.Bids[b].Node] += Result.clearedUp["Zonal"][t][b] 
        for b in Data.Bids.downBids:
            if Data.Bids[b].Participant != "Re-dispatch":
                DA_adjusted[t][Data.Bids[b].Node] -= Result.clearedDown["Zonal"][t][b]

    Data.System.NetVolumes["Zonal"] = DA_adjusted
    
    Redispatch(Data,Result,day,"Post zonal")





