"""
Created on Wed Nov 10 2022

Anders Ryssdal and Victor Aasvær

Zone clearing model
"""
import pyomo.environ as pyo
import time
from Flex_supportFunctions import timeString

def ZoneClearing(Data,Result,day,penalty = 50):
    #Tracking running time
    startTime = time.time()
    print("Initilalizing zone clearing")
    
    #Create the model object
    model = pyo.ConcreteModel()
    
    #%% Model sets  
    model.Periods = pyo.Set(initialize = list(range((day-1)*24+1,day*24+1)))                                               #T
    model.Participants_Battery = pyo.Set(initialize = list(Data.Participants.types["Battery"]))         #I^(Batt)
    model.Participants_Aggregator = pyo.Set(initialize = list(Data.Participants.types["Aggregator"]))   #I^(Aggr)  
    
    def upBids(model):
        for b in Data.Bids.upBids:
            if Data.Bids[b].Participant != "Re-dispatch":
                yield b
    model.upBids = pyo.Set(initialize=upBids)
    
    def downBids(model):
        for b in Data.Bids.downBids:
            if Data.Bids[b].Participant != "Re-dispatch":
                yield b
    model.downBids = pyo.Set(initialize=downBids)
                                          
    #The zone sets are defined as two-dimensional sets
    def zoneSets(model):
        for t in model.Periods:
            for z in list(Data.Zones.nodes[t].keys()):
                yield (z,t)
    model.Zones_2dim = pyo.Set(dimen=2,initialize = zoneSets)                               #Z_t
    
    #Line sets are also two dimensional
    def lineSets(model):
        for t in model.Periods:
            for l in Data.Zones.cutLines[t]:
                yield (l,t)
    model.Lines_2dim = pyo.Set(dimen=2,initialize = lineSets)                               #L_t
    
    
    #%%Model variables
    model.clearedUp = pyo.Var(model.upBids,model.Periods,within=pyo.NonNegativeReals)                                         
    model.clearedDown = pyo.Var(model.downBids,model.Periods,within=pyo.NonNegativeReals)                                         
    model.flow = pyo.Var(model.Lines_2dim)
    model.congestion = pyo.Var(model.Lines_2dim,within=pyo.NonNegativeReals)
    model.prod = pyo.Var(model.Zones_2dim)
    model.charge = pyo.Var(model.Participants_Battery,model.Periods,within=pyo.NonNegativeReals)
    
    #%%Objective functions
    def ObjFunc(model):
        return sum(model.clearedUp[b,t]*Data.Bids[b].Price[t] for b in model.upBids for t in model.Periods ) + sum(model.clearedDown[b,t]*Data.Bids[b].Price[t]  for b in model.downBids for t in model.Periods) + sum(model.congestion[l,t] for t in model.Periods for l in Data.Zones.cutLines[t])*penalty
    model.obj = pyo.Objective(rule=ObjFunc,sense=pyo.minimize)
    
    
    #%% Model constraints
    
    #b: The market must keep the energy balance (note that we are excluding re-dispatch in this model)
    def marketBalance_rule(model,t):
        return sum(model.clearedUp[b,t] for b in model.upBids) - sum(model.clearedDown[b,t] for b in model.downBids) == 0
    model.marketBalance_cons = pyo.Constraint(model.Periods,rule=marketBalance_rule)
    
    #c: Find net production in each zone
    def netProduction_rule(model,z,t):
        return sum(Data.System.DA_volumes[t][n]["Net"] + sum(model.clearedUp[b,t] for b in Data.Bids.nodeBids[n] if b in model.upBids) - sum(model.clearedDown[b,t] for b in Data.Bids.nodeBids[n] if b in model.downBids) for n in Data.Zones.nodes[t][z])== model.prod[z,t]
    model.netProduction_cons = pyo.Constraint(model.Zones_2dim,rule=netProduction_rule)

    #d: Bid sizes restrict the clearing
    def bidSizes_rule1(model,b,t):
        return model.clearedUp[b,t] <= Data.Bids[b].Volume[t]
    model.bidSizes_cons1 = pyo.Constraint(model.upBids,model.Periods,rule=bidSizes_rule1)
    
    def bidSizes_rule2(model,b,t):
        return model.clearedDown[b,t] <= Data.Bids[b].Volume[t]
    model.bidSizes_cons2 = pyo.Constraint(model.downBids,model.Periods,rule=bidSizes_rule2)

    #e: Find line flow
    def lineFlow_rule(model, l, t):
        return model.flow[l,t] == sum(Data.ZPTDFs[t][l][z]*model.prod[z,t] for z in Data.Zones.nodes[t].keys())
    model.lineFlow_cons = pyo.Constraint(model.Lines_2dim, rule=lineFlow_rule)
    
    #f: Line capacity
    def lineCap_rule_1(model,l,t):
        return model.flow[l,t] <= Data.System.Lines[l].Capacity + model.congestion[l,t]
    model.lineCap_cons_1 = pyo.Constraint(model.Lines_2dim,rule=lineCap_rule_1)
 
    
    def lineCap_rule_2(model,l,t):
        return -model.flow[l,t] <= Data.System.Lines[l].Capacity + model.congestion[l,t]
    model.lineCap_cons_2 = pyo.Constraint(model.Lines_2dim,rule=lineCap_rule_2)
    
    #g: Battery storage constraints
    def batteryStorage_rule(model,i,t):
        if t%24 == 1:
            return model.charge[i,t] == Data.Participants[i].Size/2   
        else:
            return model.charge[i,t] <= Data.Participants[i].Size
    model.batteryStorage_cons = pyo.Constraint(model.Participants_Battery,model.Periods,rule = batteryStorage_rule)
    
    #i: State of charge updated
    def batteryCharge_rule(model,i,t):
        if t%24 == 1:
            return pyo.Constraint.Skip
        else:
            return model.charge[i,t] == model.charge[i,t-1] - sum( model.clearedUp[b,t]/Data.Participants.batteryEfficiency["Discharge"] for b in Data.Bids.participantBids[i] if Data.Bids[b].Direction == "Up") + sum(model.clearedDown[b,t] * Data.Participants.batteryEfficiency["Charge"] for b in Data.Bids.participantBids[i] if Data.Bids[b].Direction == "Down") 
    model.batteryCharge_cons = pyo.Constraint(model.Participants_Battery,model.Periods,rule = batteryCharge_rule)
    
    #j: Aggregators must adjust up again after adjusting down. 
    def Aggregator_rule1(model,i,t):
        if t%24 > 19 or t%24 < 1:
            return pyo.Constraint.Skip
        return sum( sum(model.clearedUp[b,t+j] for b in Data.Bids.participantBids[i] if Data.Bids[b].Direction == "Up") - sum(model.clearedDown[b,t+j] for b in Data.Bids.participantBids[i] if Data.Bids[b].Direction == "Down") for j in range(6)) <= Data.Participants[i].Size*6*0.2 
    model.Aggregator_cons1 = pyo.Constraint(model.Participants_Aggregator,model.Periods, rule = Aggregator_rule1)
    
    def Aggregator_rule2(model,i):
        return sum(sum(model.clearedDown[b,t] for b in Data.Bids.participantBids[i] if Data.Bids[b].Direction == "Down") - sum(model.clearedUp[b,t] for b in Data.Bids.participantBids[i] if Data.Bids[b].Direction == "Up") for t in model.Periods) <= Data.Participants[i].Size * len(model.Periods) * 0.1
    model.Aggregator_cons2 = pyo.Constraint(model.Participants_Aggregator, rule = Aggregator_rule2)
    
    
    print("Initilialize finished after {} \n".format(timeString(time.time()-startTime)))
    
    #%% Solving the problem
    startTime =time.time()
    print("Running zone clearing")
    
    #Solving
    model.dual = pyo.Suffix(direction = pyo.Suffix.IMPORT_EXPORT)
    opt = pyo.SolverFactory("gurobi")
    result=opt.solve(model,tee=False)
    

    print("Model run finished after {} \n".format(timeString(time.time()-startTime)))
    
    Result.read_zonal(model,Data)
    return model
