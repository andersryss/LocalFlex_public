# -*- coding: utf-8 -*-
"""
Created on Wed Oct 19 09:39:58 2022

Anders Ryssdal and Victor Aasvær
"""

import copy





def DA_at_node(Data, t, node):
    return abs(Data.System.DA_volumes[t][node]['Net'])


def DA_in_zone(Data, t, z, z_to_n):
    num = 0
    for n in z_to_n[z]:
        num += DA_at_node(Data, t, n)
    return num 

def is_intra_zonal(Data, t, line,z_to_n):
    from_node = Data.System.Nodes[Data.System.Lines[line].From].ID
    to_node = Data.System.Nodes[Data.System.Lines[line].To].ID
    for z in list(z_to_n.keys()):
        if from_node in z_to_n[z]:
            from_zone = z
        if to_node in z_to_n[z]:
            to_zone = z
        
    if to_zone == from_zone:
        return True
    else:
        return False
    

def calc_GSK(Data, t,z_to_n):
    GSK = {}
    DA_at_Node = {}
    for node in Data.System.getNodeList('All'):
        DA_at_Node[node] = DA_at_node(Data, t, node)
        
    DA_in_Zone = {}
    for zone in list(z_to_n.keys()):
        DA_in_Zone[zone] = DA_in_zone(Data, t, zone,z_to_n)

    for node in Data.System.getNodeList('All'):
        GSK[node] = {}
        for zone in list(z_to_n.keys()):
            if node in z_to_n[zone]:
                if DA_in_Zone[zone] == 0:
                    GSK[node][zone] = 0
                else:
                    GSK[node][zone] = DA_at_Node[node]/DA_in_Zone[zone]
            else:
                GSK[node][zone] = 0
    return GSK
    
    

def calc_ZPTDF(Data, t):

    z_to_n = copy.deepcopy(Data.Zones.nodes[t])
    #Adding the fake zones 
    ind = len(z_to_n) + 1
    for node in Data.System.getNodeList("Not flex"):
        z_to_n[ind] = [node]
        ind += 1
            
    ZPTDF = {}
    GSK = calc_GSK(Data, t,z_to_n)
    for line in Data.System.getLineList('All'):
        if is_intra_zonal(Data, t, line,z_to_n):
            continue
        ZPTDF[line] = {}
        for zone in list(z_to_n.keys()):
            ZPTDF[line][zone] = sum([Data.System.PTDFs[line][n]*GSK[n][zone] for n in z_to_n[zone]])
            
    return ZPTDF
    
    