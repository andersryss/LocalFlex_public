# -*- coding: utf-8 -*-
"""
Created on Sat Nov 26 2022

Victor and Anders

Functions used in flex project
"""
import numpy as np
from numpy import matmul
import pandas as pd
import math
import os,sys
from pathlib import Path
import json 

#%% Load flow calculations
def LoadFlow(data, Type='DA'):
    #Create empty array for PTDFs and get dict of PTDFs
    PTDF = np.empty((len(data.System.Lines), len(data.System.Nodes)))
    PTDF_dict = data.System.PTDFs
    
    #Define result dict for flow per period
    flow = {t: {} for t in data.Periods}
    
    #Convert PTDF dict to array
    for l in data.System.Lines.values():
        PTDF[l.ID] = np.array(list(PTDF_dict[l.ID].values()))
    
    NP_dict = data.System.NetVolumes[Type]
    
    #Calculate flow and append to flow dict
    for t in list(flow.keys()):
        flow_array = matmul(PTDF, list(NP_dict[t].values()))
        res = {}
        for l in data.System.Lines.values():
            res[l.ID] = flow_array[l.ID]
        flow[t] = res
    return flow


#%% Save and load objects that use json. They should only take in our custom objects, and have possibility of pushing to git
def Save(obj,filename,folder=False,push=False):
    #Construct the file path
    if not folder:       
        folder = []
    if isinstance(folder,list):
        path=Path(".")
        for s in folder:
            path = path / s
        path = path /filename
    else:
        path = Path(".") / folder / filename
    
    #Save object as JSON
    
    Dict = obj.to_dict() 
    #Check if file size is too large. If it is, save dictionary components seperately
    if len(json.dumps(Dict)) > 95000000:
        if path.is_file():
            os.remove(path)
            os.makedirs(path,exist_ok=True)
        elif not os.path.exists(path):
            os.makedirs(path,exist_ok=True)
        for key,val in Dict.items():
            subPath = path / key
            with open(subPath,"w") as file:
                json.dump(val,file)
    else:
        with open(path,"w") as file:
            json.dump(Dict,file)
    
    if push:
        gitUpload(path)
    
def Load(Type,filename,folder=False):
    #Construct the file path
    if not folder:
        folder= []
    elif isinstance(folder,str):
        folder = [folder]
    if isinstance(folder,list):
        path = Path(".")     
        for s in folder:
            path = path / s
        path = path / filename
    
    # Read the file as JSON
    if not os.path.isdir(path):
        with open(path, "r") as file:
            Dict = json.load(file)
    else: 
        Dict = dict()
        for root,dirs,files in os.walk(path):
            for item in files:
                with open(path/item, "r") as file:
                    Dict[item]=json.load(file)
            
    return Type.from_dict(Dict)


#%%Class made to mute the print commands from the timer object when they are not wanted. If this was not used, the command window would print "model has started running" for every iteration of the baseModel
#This method of hiding print calls was gathered from the internet and is not our own creation


class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

def timeString(seconds):
    hours = math.floor(seconds/3600)
    minutes = math.floor((seconds-hours*3600)/60)
    seconds = round(seconds - hours*3600 - minutes*60)
    
    if (hours>0):
        string = "{:d} hours, {:d} minutes and {:d} seconds\n".format(hours,minutes,seconds)
    elif(minutes >0):
        string = "{:d} minutes and {:d} seconds\n".format(minutes,seconds)
    else:
        string = "{:.1f} seconds\n".format(seconds)
    
    return string

#Function returning path string of certain DA excel files
def DA_path(Range):
    i = 1
    paths = []
    for root, dirs, files in os.walk(os.getcwd()+"\\NordPool datasets",topdown=False):
            for name in files:
                if i in Range:
                    paths.append(os.path.join(root, name))
                i += 1
    return paths
 #%%git functions           
def gitUpload(filename="."):
    
    os.system('git add "{}"'.format(filename))
    
    if filename==".":
        filename = "all changes"
    
    os.system('git commit -m "Added {} to the repository"'.format(filename))
    
    os.system("git pull")
    
    os.system('git add .')
    
    os.system('git commit -m "Potential merging"')
    
    os.system("git push")
    
