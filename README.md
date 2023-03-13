# LocalFlex_public
This repository contains the code, optimization models and input data used in the research paper []. The repository is intended to be publicly available for anyone who wants to reproduce, verify, or build upon the findings presented in the paper.

Full paper doi: 

main.py can be used to load the results used in the paper, or to run the models on new data (only the bids will change) 

Objects:
  The The input data and results are stored and treated in the form of objects
    Flex_data.py describes a class containing all data that is relevant for the models and algorithms to run, including other objects. 
    Flex_Bids.py describes a class containing all bids used in the models. Each bid is represented by a class object, also included in the file
    Flex_Participants.py describes a class containing all market participants. Each participant is represented by a class object, also included in the file
    Flex_System.py describes a class containing the grid system data and information about the DA volumes. Each node and each line is represented by their own class object,also included in the file
    Flex_zones.py describes a class containing the zonal configurations. It also describes the zonal partitioning algorithm, hich is a part of a "Heuristic" class
    Flex_Result.py describes the class storing all results from the models. 
    
Models:
  There are three files containing the optimization models used in the paper
    Flex_nodeClearing.py contains a function running the Nodal FM model
    Flex_zoneClearing.py contains a function running the Zonal FM model
    Flex_redispatch.py contains one function running the re-dispatch model (BAU case), and another function that runs step 4 in the Zonal FM case, also using the re-dispatch model
    
Other functions:
  There are some functions that are neither class methods nor directly responsible for running a function. They are stored in seperate files from those above
    Flex_supportFunctions.py include several functions that are needed various places in the system. For example, save and load functions using json, and a load flow function
    Flex_calculatePTDFs.py include a function calculating zonal PTDFs based on the nodal PTDFs and a zonal configuration
    Flex_metaFunctions.py include functions for running models and sensitivities across several days

Excel documents: 
    Input data.xlsx include information about the whole grid, market participants and PTDFs. Used by the Data object
    Regional grid.xlsx contains information about the DS grid and the participants. Information is overlapping with the "Input data" document, but this is used by the Bids object
    
Folders
    Nordpool datasets contains excel documents with DA volumes for the 14 days used in the paper
    Results is used to store the results and data objects. It contains the results used in the paper 
  
    
