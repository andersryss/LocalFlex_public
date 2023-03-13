"""
Created on Fri Nov 11 2022

Anders Ryssdal and Victor Aasvær

Bid generator for bids to be part of input data
"""
import pandas as pd
import numpy as np
import collections

#Object containing bid information 
class Bids:
    def __init__(self):
        self.fullDict = dict()
        self.upBids = list()
        self.downBids = list()
        self.nodeBids = collections.defaultdict(list)
        self.participantBids = collections.defaultdict(list)
        
    def __getitem__(self, ID):
        return self.fullDict[ID]

        
    def to_dict(self):
        Dict = {}
        for ID,bid in self.fullDict.items():
            Dict[ID] = bid.to_dict()
        return Dict
    
    @classmethod
    def from_dict(cls,Dict):
        bidCollection = cls()      
        for ID,subDict in Dict.items():
            bid = Bid.from_dict(subDict)
            bidCollection.fullDict[ID] = bid
            bidCollection.nodeBids[bid.Node].append(bid.ID)
            bidCollection.participantBids[bid.Participant].append(bid.ID)
            if bid.Direction == "Up":
                bidCollection.upBids.append(bid.ID)
            else:
                bidCollection.downBids.append(bid.ID)
        return bidCollection
        
            
    #Function calculating bids based on bid behaviors, participant sizes and participant cost scaling
    def createBids(self,periods):
        
        #Data import
        partDF = pd.read_excel("Regional grid.xlsx",sheet_name="Participants")
        
        #Bid behaviors (up,down)
        nBids = {"Aggregator":(3,2), "Battery":(2,2),"Industry":(1,1),"Intermittent":(1,1)}           
        avgCost = {"Aggregator":([2,8,15],[5,15]), "Battery":([2,5],[2,5]),"Industry":([10],[10]),"Intermittent":([-10],[-10])}
        bidSize = {"Aggregator":([0.05,0.1,0.25],[0.1,0.25]), "Battery":([0.2,0.8],[0.2,0.8]),"Industry":([0.3],[0.1]),"Intermittent":([0.15],[0.15])}
            
        for pIndex,pRow in partDF.iterrows():
            if pRow["Type"] in nBids:
                participant = pRow["Participant"]
                Type = pRow["Type"]
            
                #Down bids
                for b in range(nBids[Type][1]):
                    ID = "p" + str(participant) + "b" + str(b+1) + "D"
                    Volume = round(bidSize[Type][1][b] * pRow["Size"])
                    Cost = round(avgCost[Type][1][b] * pRow["Cost scaling"])
                    self.fullDict[ID] = Bid(ID,"Down",participant,pRow["Node"],Volume,Cost,periods)
                    self.downBids.append(ID)
                    self.nodeBids[pRow["Node"]].append(ID)
                    self.participantBids[participant].append(ID)


                #Up bids 
                for b in range(nBids[Type][0]):
                    ID = "p" + str(participant) + "b" + str(b+1) + "U"
                    Volume = round(bidSize[Type][0][b] * pRow["Size"])
                    Cost = round(avgCost[Type][0][b] * pRow["Cost scaling"])
                    self.fullDict[ID] = Bid(ID,"Up",participant,pRow["Node"],Volume,Cost,periods)
                    self.upBids.append(ID)
                    self.nodeBids[pRow["Node"]].append(ID)
                    self.participantBids[participant].append(ID)
                
    #Copy the bids object and change the bids according to some stochastic rules         
    def createNoise(self,Participants):

        #Defining the stochastic behavior (down,up)
        p_remove = {"Aggregator":(0.3,0), "Battery":(0.3,0.3),"Industry":(0.2,0.7),"Intermittent":(0.5,0.5)}
        p_increaseV = {"Aggregator":(0.25,0.25), "Battery":(0.2,0.2),"Industry":(0.2,0.05),"Intermittent":(0.2,0.2)}
        p_decreaseV = {"Aggregator":(0.35,0.1), "Battery":(0.2,0.2),"Industry":(0.2,0.2),"Intermittent":(0.2,0.2)}
        
        volumeChange = 0.4          #Percentage increase or decrease of bid volume
        costDeviation = 0.25        #Used as parameter when using normal distribution to find new costs
        
        for ID,bid in self.fullDict.items():
            if bid.Participant != "Re-dispatch":
                pType = Participants[bid.Participant].Type 
                
                if bid.Direction == "Down":
                    bKey = 0
                else:
                    bKey = 1
                
                for t in bid.Volume:
                    bid.Price[t] = round(np.random.normal(bid.Price[t],abs(bid.Price[t])*costDeviation),1)
                    
                    p = np.random.random()
                    if p < p_remove[pType][bKey]:
                        bid.Volume[t] = 0
                    elif p < p_remove[pType][bKey] + p_increaseV[pType][bKey]:
                            bid.Volume[t] = bid.Volume[t] * (1+volumeChange)
                    elif p < p_remove[pType][bKey] + p_increaseV[pType][bKey] + p_decreaseV[pType][bKey]:
                        bid.Volume[t] = bid.Volume[t] * (1-volumeChange)
    
class Bid:
    def __init__(self,ID,Direction,Participant,Node,Volume,Price,Periods):
        self.ID = ID
        self.Direction = Direction      
        self.Participant = Participant
        self.Node = Node
        
        self.Volume = {t:Volume for t in Periods}
        self.Price = {t:Price for t in Periods}
        
    def to_dict(self):
        Dict = {}
        for name,value in vars(self).items():
            Dict[name] = value
        return Dict
    
    @classmethod
    def from_dict(cls,Dict):
        volumeDict = {int(key):val for key,val in Dict["Volume"].items()}
        priceDict = {int(key):val for key,val in Dict["Price"].items()}
        
        bid = cls(Dict["ID"],Dict["Direction"],Dict["Participant"],Dict["Node"],0,0,[1])
        bid.Volume = volumeDict
        bid.Price = priceDict
        
        return bid
        
    #Function changing the cost/price of the bid
    def changePrice(self,newPrice,period="All"):
        if period == "All":
            for t in self.Price:
                self.Price[t] = newPrice
        else:
            self.Price[period] = newPrice
    
    #Function changing the volume of the bid
    def changeVolume(self,newVol,period="All"):
        if period == "All":
            for t in self.Volume:
                self.Volume[t] = newVol
        else:
            self.Volume[period] = newVol
            
    #Function scaling the cost/price of the bid
    def scalePrice(self,scaling):
        for t in self.Price:
            self.Price[t] = self.Price[t] * scaling
    
    def scaleVolume(self,scaling):
        for t in self.Volume:
            self.Volume[t] = self.Volume[t] * scaling
            