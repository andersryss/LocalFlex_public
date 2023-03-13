"""
Created on Thu Oct 13 2022

Anders Ryssdal and Victor Aasvær

Importing and storing parameters and data for the models
"""
from Flex_Zones import Zones,Heuristic
from Flex_System import System,Line,Node
from Flex_Participants import Participants,Participant
from Flex_Bids import Bids,Bid
from Flex_calculatePTDFs import calc_ZPTDF
from Flex_supportFunctions import DA_path,timeString,HiddenPrints

import time
import pandas as pd
import numpy as np
from geopy import distance


class Data:
    def __init__(self,days):
        
        self.days = days
        self.Periods = list(t for t in range(1,days*24+1))                      #T
        
        self.Participants = Participants()                                      #Object with market participants 
        self.System = System()                                                  #Object containg the DA and grid system, including the nodes and power lines                                                      #Dictionary with pandaPower networks, one for each period                                           
        self.Bids = Bids()                                                      #Object with bid data
        self.Zones = Zones()                                                    #Object with the zonal configurations for each period
        self.ZPTDFs = {}                                                        #Object storing zonal PTDFs for each hour
    
    @classmethod
    def create(cls,days,nZones=5,minNodes=5):
        timer = time.time()
        
        Data = cls(days)
        Data.Import()   
        with HiddenPrints():
            Data.runZonePartitioning(nZones,minNodes)
            Data.fill_ZPTDFs()
        
        print("Data object created in {}".format(timeString(time.time()-timer)))
        return Data
    
    #Method converting object to a dictionary
    def to_dict(self):
        Dict = {}
        
        Dict["days"] = self.days
        Dict["Participants"] = self.Participants.to_dict()
        Dict["System"] = self.System.to_dict()
        Dict["Bids"] = self.Bids.to_dict()
        Dict["Zones"] = self.Zones.to_dict()
        
        return Dict
    
    @classmethod
    def from_dict(cls,Dict,Grids=False):
        Data = cls(Dict["days"])
        
        Data.Participants = Participants.from_dict(Dict["Participants"])
        Data.System = System.from_dict(Dict["System"])
        Data.Bids = Bids.from_dict(Dict["Bids"])
        Data.Zones = Zones.from_dict(Dict["Zones"])
        Data.fill_ZPTDFs()
        return Data        

    #%%Function importing all data except Zones and NodesDistributed       
    def Import(self):
        start_import = time.time()
        print("Importing data")
        
        #variable needed but not specified in input data
        base_MVA = 100   
        redispatch_cost = 50
        
        #Names of the files to be imported
        filename = 'Input data.xlsx'     
        
        #Import data and store it as dataframes
        buses = pd.read_excel(filename, sheet_name="Nodes")
        lines = pd.read_excel(filename, sheet_name="Lines")
        geodata = pd.read_excel(filename, sheet_name="Node coordinates")
        participantData = pd.read_excel(filename,sheet_name = "Participants")
        generators = pd.read_excel(filename, sheet_name="Generators")
        
        #Fill Node data
        for _, bus in buses.iterrows(): #Import node data
            #Find geographical position 
            lat = geodata[geodata.bus_name == bus.bus_id]['lat'].iloc[0]
            long = geodata[geodata.bus_name == bus.bus_id]['lon'].iloc[0]
            
            if buses["bus_id"].str.contains("R_"+bus.bus_id+"_1").any():
                HostNode = True
            else:
                HostNode = False
            node = Node(bus.bus_id,bus.baseKV,bus.type,(long,lat), bus.zone,bus.Flex_grid,HostNode,bus.Load_share)             
            self.System.Nodes[bus.bus_id] = node
            
            
        
        #Create lines and add to System
        line_id = 0 #Create id to give lines name
        for _, line in lines.iterrows(): #Import line data
            
            #Calculate line length
            bus_from_coords = self.System.Nodes[line.bus_from].geoData
            bus_to_coords = self.System.Nodes[line.bus_from].geoData
            dist_km = distance.distance(bus_from_coords, bus_to_coords).km
            if dist_km == 0:
                dist_km = 10e-2
            
            #Find p.u. bases
            V_base_kv = min(self.System.Nodes[line.bus_from].Voltage, self.System.Nodes[line.bus_to].Voltage)
            Z_ohm_base = V_base_kv**2/base_MVA
            
            r = line.r*Z_ohm_base/float(dist_km)
            x = line.x*Z_ohm_base/float(dist_km)
            
            #Find line capacity
            if r == 0:
                Cap = float('inf')
            else:
                Cap = line.rate_a/V_base_kv/np.sqrt(3)
            temp_Line = Line(line_id,line.bus_from,line.bus_to,line.type,Cap*V_base_kv*np.sqrt(3),dist_km,line.b,x,r,0,line.Flex_grid, Cap)
            self.System.Lines[line_id] = temp_Line
            line_id += 1
 

        
        #Fill DA_volumes
        self.System.NetVolumes['DA'] = {}
        DA_paths = DA_path(list(range(1,self.days+1)))
        t = 1
        for path in DA_paths:
            for j in range(1,25):
                sheet_name = 'period' + str(j)
                volumes = pd.read_excel(path, sheet_name=sheet_name)
                self.System.DA_volumes[t] = {}
                self.System.NetVolumes['DA'][t] = {} 
                for n in self.System.Nodes.values():
                    if n.isHost:
                        load = 0
                        prod = volumes[volumes.bus_id == n.ID]['Production'].iloc[0]
                    elif "R_" in n.ID:
                        prod = 0
                        load = volumes[volumes.bus_id == n.ID[2:n.ID.index("_",2)]]['Load'].iloc[0]*n.loadShare
                    else:
                        prod = volumes[volumes.bus_id == n.ID]['Production'].iloc[0]
                        load = volumes[volumes.bus_id == n.ID]['Load'].iloc[0]
                        
                    self.System.DA_volumes[t][n.ID] = {"Production": prod,"Load": load,"Net": prod-load}
                    self.System.NetVolumes['DA'][t][n.ID] = prod-load
                t += 1
        
        #Fill in Participants 
        for index, row in participantData.iterrows():
            part = Participant(row["Participant"],row["Type"],row["Node"],row["Size"],row["Cost scaling"])
            self.Participants.fullDict[part.ID] = part
            self.Participants.types[part.Type].append(part.ID)
            self.Participants.nodes[part.Node].append(part.ID)
            
        #Create bids
        self.Bids.createBids(self.Periods)
        self.Bids.createNoise(self.Participants)
        
        #Create re-dispatch bids 
        for n in self.System.Nodes.values():
            bidID = "Redispatch Down, " + n.ID
            bid = Bid(bidID,"Down","Re-dispatch",n.ID,0,redispatch_cost,self.Periods)
           
            for t in self.Periods:
                bid.changeVolume(self.System.DA_volumes[t][n.ID]["Production"],t)
            self.Bids.fullDict[bidID] = bid
            self.Bids.downBids.append(bidID)
            self.Bids.nodeBids[n.ID].append(bidID)
            self.Bids.participantBids["Re-dispatch"].append(bidID)
            
            bidID = "Redispatch Up, " + n.ID
            bid = Bid(bidID,"Up","Re-dispatch",n.ID,0,redispatch_cost,self.Periods)
            for t in self.Periods:
                bid.changeVolume(self.System.DA_volumes[t][n.ID]["Load"],t)
            self.Bids.fullDict[bidID] = bid
            self.Bids.upBids.append(bidID)
            self.Bids.nodeBids[n.ID].append(bidID)
            self.Bids.participantBids["Re-dispatch"].append(bidID)

        #Read PTDF matrix
        lines = [l.ID for l in self.System.Lines.values()]
        nodes = [n.ID for n in self.System.Nodes.values()]
        PTDF_df = pd.read_excel(filename, sheet_name="PTDF",names=nodes, header=None)
        PTDF_df.index = lines
        
        #Create dictionary with lines as outer key and nodes as inner key for PTDFs
        self.System.PTDFs = PTDF_df.to_dict('index')
        
        end_import = time.time()

        print('Finished after {} s\n'.format(round(end_import - start_import)))        

            
   
    #%%Splitting into zones and storing information in Zones and NodesDistributed
    def runZonePartitioning(self,nZones,minNodes): 
        self.Heuristics={}
        for t in self.Periods:
            partition = Heuristic(self,nZones,minNodes,t)
            self.Heuristics[t]=partition
            self.Zones.extractZones(self, partition, t)
        
    #%%Fill in self.ZPTDFs
    def fill_ZPTDFs(self):
        print("Calculating ZPTDFs for all periods")
        start_ptdf = time.time()
        for t in self.Periods:
            self.ZPTDFs[t] = calc_ZPTDF(self, t)
        print('Finished calculating zonal PTDFs after {:.2f} s\n'.format(time.time() - start_ptdf))
    
    def getZoneParticipants(self,z,t):
        participants = set()
        nodes = self.Zones.nodes[t][z]
        for n in nodes:
            participants = participants.union(self.Participants.nodes[n])
        return participants
    
    