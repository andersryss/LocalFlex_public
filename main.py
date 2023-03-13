"""
This is the main code file, used to run load results based on an ID, or run the models again and store the results

Creating a new data object will give new results, as the bids will be different. 
Therefore, both the option to view previous results and to run models on a new data object will be present below

"""
from Flex_metaFunctions import *


#%% Load the results used in the paper
runID= "Final"                                              #The runID used for the results presented in the paper

results,data = loadResults(runID)                           #Load the result objects into the "results" dictionary. The data object used in the runs is also loaded




#%%Run the models again, using a new data object where bids are different
runID = "New"

results_new,data_new = runAll(runID)                        #Both base cases and sensitivities are run in runAll()


#%% Save the new results and data object
Save(data_new,"Data_{}".format(runID),folder=["Results"])
for key,val in results_new.items():
    if isinstance(val,dict):
        for key2,val2 in val.items():
            Save(val2,f"{key2}_{runID}",folder={"Results",key})
    else:
        Save(val,f"_{runID}",folder={"Results",key})