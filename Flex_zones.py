# -*- coding: utf-8 -*-
"""
Created on Fri Oct 21 11:48:30 2022

File containing both the zone partitioning heuristic (Heuristic) and the object where the result is stored (Zones)
"""
import networkx as nx
from Flex_supportFunctions import LoadFlow

#%% Object storing the zones created fro the various time periods. The period is the outer key for each property
class Zones:
    def __init__(self):
        
        self.nodes = dict()                 # Zone as the key and list with the corresponding nodes as the value
        self.cutLines = dict()              # List with the cut lines for each period
  
    #Function extracting the zone data from a Heuristic object
    def extractZones(self,Data,obj,t):
        self.nodes[t] = {index+1: obj.NodesDistributed[zoneID] for index, zoneID in enumerate(obj.zoneID[obj.nIterations])}
        
        self.cutLines[t] = list()
        for i in obj.cutLines:
            for e in obj.cutLines[i]:
                for l in Data.System.getLineList("Flex"):
                    line = Data.System.Lines[l]
                    if (e[0] == line.From and e[1] == line.To) or (e[0] == line.To and e[1] == line.From):
                        self.cutLines[t].append(line.ID)
        
    def to_dict(self):
        Dict = {}
        for name,value in vars(self).items():
            Dict[name] = value
        return Dict
    
    @classmethod
    def from_dict(cls,Dict):
        obj = cls()
        
        for t in Dict["nodes"]:
            obj.nodes[int(t)] = {int(z):Dict["nodes"][t][z] for z in Dict["nodes"][t]}
            obj.cutLines[int(t)] = [int(l) for l in Dict["cutLines"][t]]       
        return obj
    
#%% Object running and keeping track of the zonePartitioning heuristic for one specific hour, logging every iteration with its respective key in order to keep track of the algorithm
class Heuristic:
    def __init__(self, Data, nZones, minNodes, t):

        # Information about the partition process:
        self.minNodes = minNodes
        self.nZones = nZones

        # Tracking the algorithm
        self.nIterations = 0                # Should equal number of zones - 1 if the run finished
        self.zoneID = {}                    # Dict with the algorithm iteration as key, storing the ID's of the zones returned in each iteration 
        self.zoneChoice = {}                # Dict with the algorithm iteration as key, storing the zone chosen to be split in each iteration
        
        #Information about the zones
        self.zones = {}                     # Dict with the zone ID as key, storing the corresponding networkx graphs
        self.zoneSizes = {}                 # Dict with the zone ID as key, storing the corresponding zone sizes 
        self.congestedLines = {}            # Dict with the zone ID as key, storing the congested lines within that zone
        self.NodesDistributed = {}          # Dict with the zone ID as key, storing the nodes belonging to the respective zone
        
        #Cut information
        self.cutLines = {}                  # Dict with the algorithm iteration as key, storing the lines cut in each iteration     
        self.cutValue = {}                  # Dict with the algorithm iteration as key, storing the cut value for each iteration
        self.partitionValue = 0             # Accumulated value from the zone splitting



    
        #%%Finding congested lines and creating a Graph object
        
        flow = LoadFlow(Data,"DA")[t]
        lines = Data.System.getLineList("Flex")
        congestedLines = []
        for l in lines:
            line = Data.System.Lines[l]
            if line.Capacity < abs(flow[line.ID]):
                congestedLines.append(line)
        Graph = nx.Graph()
        Graph.add_nodes_from([n for n in Data.System.getNodeList('Flex')])
        Graph.add_edges_from([(Data.System.Lines[l].From,Data.System.Lines[l].To) for l in lines])
        self.congestedLines[1] = [l for l in congestedLines]
        for l in self.congestedLines[1]:
            Graph.edges[l.From, l.To]['congestion'] =  abs(flow[l.ID])-l.Capacity
        print("\n")
        
        #%%Run the zone partitioning algorithm, outer layer
        self.zoneID[0] = [1]
        self.zones[1] = Graph
        self.zoneSizes[1] = len(Graph.nodes)
        self.NodesDistributed[1] = list(Graph.nodes)
        i = 0
        print("Zone partitioning for period {}:".format(t))
        while i < self.nZones-1:
            i += 1

            splitOptions = []
            isCongestion = False  
            self.zoneChoice[i] = 0
            for ID in self.zoneID[i-1]:
                nCongested = len(self.congestedLines[ID])
                nNodes = self.zoneSizes[ID]
                if nCongested > 0 and nNodes >= self.minNodes*2:
                    splitOptions.append(ID)
                elif nCongested > 0 and not isCongestion:
                    isCongestion = True

            if len(splitOptions) == 0 and isCongestion:
                print("Stopping after {} iterations because congestion only exists within zones that are too small to divide further".format(i-1))
                self.nZones = i
                break
            elif len(splitOptions) == 0 and i == 1:
                print("There is no congestion in the system, so no zones are created")
                self.nZones = i
                return
            elif len(splitOptions) == 0:
                print("Stopping after {} iterations because all congestion has been cut away by zone borders".format(i-1))
                self.nZones = i
                break

            # Split zones according to heuristic algorithm, try for each zone that is possible to split
            self.cutValue[i] = 0
            foundSolution = False
            for z in splitOptions:    
                g1,g2,cutValue,cutLines= targetedPartition(self.zones[z], self.minNodes, self.congestedLines[z])
                if cutValue> self.cutValue[i]:
                    self.cutValue[i] = cutValue
                    self.cutLines[i] = list(cutLines)
                    self.zoneChoice[i] = z
                    G1 = g1
                    G2 = g2
                    foundSolution = True
            
            if foundSolution:
                self.nIterations = i
                
                self.zoneID[i] = [z for z in self.zoneID[i-1]if z != self.zoneChoice[i]]
                self.zoneID[i].append(i*2)
                self.zoneID[i].append(i*2+1)

                self.zones[i*2] = G1
                self.zones[i*2+1] = G2
                self.zoneSizes[i*2] = len(G1.nodes)
                self.zoneSizes[i*2+1] = len(G2.nodes)
                self.NodesDistributed[i*2] = list(self.zones[i*2].nodes)
                self.NodesDistributed[i*2+1] = list(self.zones[i*2+1].nodes)

                self.getZoneCongestions(g1, i*2, i)
                self.getZoneCongestions(g2, i*2+1, i)

                self.partitionValue += self.cutValue[i]

            else:
                print("Stopping after {} iterations because no feasible solution was found".format(i))
                self.nZones = i
                del self.cutValue[i]
                break
                
        
        # Find number of congested lines cut and print result
        totCongested = len(self.congestedLines[1])
        nCongested = 0
        for ID in self.zoneID[self.nIterations]:
            nCongested += len(self.congestedLines[ID])
        print("Split area into {} zones, where {} of {} congested lines were cut\n".format(self.nZones, totCongested-nCongested, totCongested))
        
        
    def getZoneCongestions(self, g, zoneID, iteration):
        self.congestedLines[zoneID] = []
        for l in self.congestedLines[self.zoneChoice[iteration]]:
            if l.From in g.nodes and l.To in g.nodes:
                self.congestedLines[zoneID].append(l)


# %%The middle layer of the heuristic, tasked with splitting a zone G according to the most valuable cut


def targetedPartition(G, minNodes, congestedLines):
    bestCut = []
    bestValue = 0
    foundCut = False
    # Iterate over the congested lines within the zone G
    for l in congestedLines:
        # The cutLine() function is recursive and only returns when it has completely split G in two
        partition1, partition2, feasible, node = cutLine(G, l.From, l.To, minNodes)
        # Check if cutLine returned a feasible solution and compares with the best solution found so far
        if feasible:
            foundCut = True
            val = nx.algorithms.cut_size(G, partition1, weight="congestion")
            if val >= bestValue:
                bestCut = [partition1.copy(), partition2.copy()]
                bestValue = val
    if not foundCut:
        return (nx.Graph(), nx.Graph(), 0, {})
    return (nx.subgraph(G, bestCut[0]), nx.subgraph(G, bestCut[1]), bestValue, G.edges-nx.subgraph(G, bestCut[0]).edges-nx.subgraph(G, bestCut[1]).edges)

# %%The innermost layer of the heuristic. Made up of two functions


def cutLine(G, startNode, endNode, minNodes):
    SP = nx.shortest_path(G, startNode, endNode)
    G2 = G.copy()
    #Prioritize congested lines, otherwize cut in the middle of shortest path
    #for c in congestedLines:
        #if (c[0] in SP and c[1] in )
    G2.remove_edge(SP[round(len(SP)/2)-1], SP[round(len(SP)/2)])
    if nx.is_connected(G2):
        partition1, partition2, feasible, node = cutLine(G2, startNode, endNode, minNodes)
    else:
        partition1, partition2, feasible, node = findPartitions(G2, startNode, endNode, minNodes)

    if not feasible and node == startNode:
        G2 = G.copy()
        G2.remove_edge(node, SP[1])
        if nx.is_connected(G2):
            partition1, partition2, feasible, node = cutLine(G2, startNode, endNode, minNodes)
        else:
            partition1, partition2, feasible, node = findPartitions(G2, startNode, endNode, minNodes)
    elif not feasible and node == endNode:
        G2 = G.copy()
        G2.remove_edge(node, SP[-2])
        if nx.is_connected(G2):
            partition1, partition2, feasible, node = cutLine(G2, startNode, endNode, minNodes)
        else:
            partition1, partition2, feasible, node = findPartitions(G2, startNode, endNode, minNodes)

    return (partition1, partition2, feasible, node)


def findPartitions(G, n1, n2, minNodes):
    neighbors1 = set(nx.neighbors(G, n1))
    neighbors2 = set(nx.neighbors(G, n2))

    checkedNodes = set()
    connectedNodes = set()
    partitionNodes = []  # Keep track of which nodes are examined and put in which of the partition sets. Important information in case one of the partitions become too small
    if len(neighbors1) <= len(neighbors2):
        partitionNodes = [n1, n2]
        checkedNodes.add(n1)
        connectedNodes = neighbors1
    else:
        partitionNodes = [n2, n1]
        checkedNodes.add(n2)
        connectedNodes = neighbors2

    while len(connectedNodes) > 0:
        node = next(iter(connectedNodes))
        checkedNodes.add(node)
        connectedNodes.remove(node)

        nodeNeighbors = set(nx.neighbors(G, node))
        connectedNodes.update(nodeNeighbors - connectedNodes - checkedNodes)

    partition1 = checkedNodes
    partition2 = G.nodes-partition1

    if len(partition1) >= minNodes and len(partition2) >= minNodes:
        return (partition1, partition2, True, 0)
    # return the ID of the node belonging to the set that is too small:
    elif len(partition1) < minNodes:
        return (set(), set(), False, partitionNodes[0])
    else:
        return (set(), set(), False, partitionNodes[1])
