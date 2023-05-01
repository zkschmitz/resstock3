# -*- coding: utf-8 -*-
"""
Created on Sat Jun 25 12:19:00 2022

@author: Morgan Santoni-Colvin, MIT Energy Initiative
"""
# set working dir as the folder in which this script is placed
import argparse
import json
import os
import time

import numpy as np
import pandas as pd
# imrt custom functions
## HVAC modeling + associated funcs - most of these aren't used in this main script and may be unnecessary
from HVAC_model_res import HVAC_model_res, create_temp_column
from HVAC_sizing_res import HVAC_sizing_res

print('main.py: starting...')

# Get the absolute path of the current script
current_working_directory = os.getcwd()
# Get the parent folder of the current script
parent_folder_path = os.path.dirname(current_working_directory)
# print("Current working directory before change:", os.getcwd())
# Change the working directory to the parent folder
output_directory_path = os.path.join(parent_folder_path, "outputs")
os.chdir(output_directory_path)
# print("Current working directory after change:", os.getcwd())
path = os.getcwd()
print("PATH IS", path)

# inputs from CLI
parser = argparse.ArgumentParser(description="Process project name and years") 
# Project name argument
parser.add_argument("project_name", type=str, help="Project name")
# Years array argument
parser.add_argument("years", nargs="+", type=str, help="Space-separated years")
args = parser.parse_args()
project_name = args.project_name
years = args.years
if "TMY" in years:
    years.remove("TMY")
# inputs
# project_name = 'results_project_NE_zones17'
# years = ['2001'] # can expand list for as many weather years as you're interested in. These are years hourly performance is simulated for. No need to include TMY


project_names = [project_name+'_'+year for year in years]
TMY_name = project_name + '_TMY'

sizing_logic = ['Winter','Summer']
backup_type = ['Existing','Electric','NoBackup']
upgrade_names = ['ECM1','ECM2YesASHP'] # should match yml used in ResStock runs

#%% Define sub-functions that are used in multiple functions

#%%
# IF sizing_dict file does not exist:
# run sizing calculations for each archetype in the TMY data:
if 'all_sizing_dict.txt' in os.listdir(path+'/'+TMY_name):
    print('main.py: all_sizing_dict.txt already exists in ' + TMY_name + ". Importing the sizing data...")
    all_sizing_dict = json.load(open(path+'/'+TMY_name+'/all_sizing_dict.txt'))
else:
    print('main.py: all_sizing_dict.txt does not exist in ' + TMY_name + ".")
    start_time = time.time()

    all_sizing_dict = {} # dictionary of dictionaries
    print('main.py: Running sizing models...')
    print("Sizing for winter, ECM1") # each ECM1 Winter and ECM1 Summer refers to the same subset of resstock outputs
    # project_path,upgrade_name,input_folder,sizing_logic
    all_sizing_dict['Winter ECM1'] = HVAC_sizing_res(path+'/'+TMY_name,'ECM1','/inputs/ResStock_outputs/','Winter') 
    print("Sizing for summer, ECM1")
    all_sizing_dict['Summer ECM1'] = HVAC_sizing_res(path+'/'+TMY_name,'ECM1','/inputs/ResStock_outputs/','Summer')
    print("Sizing for winter, ECM2")
    all_sizing_dict['Winter ECM2YesASHP'] = HVAC_sizing_res(path+'/'+TMY_name,'ECM2YesASHP','/inputs/ResStock_outputs/','Winter')
    print("Sizing for summer, ECM2")
    all_sizing_dict['Summer ECM2YesASHP'] = HVAC_sizing_res(path+'/'+TMY_name,'ECM2YesASHP','/inputs/ResStock_outputs/','Summer')
    print("Sizing took "+ str((time.time() - start_time)/60) +" minutes." )
    # write all_sizing_dict to a text file so that next time we don't have to generate it
    json.dump(all_sizing_dict, open(path+'/'+TMY_name+"/all_sizing_dict.txt",'w'))
    print('main.py: wrote all_sizing_dict.txt to ' + path + '/' + TMY_name)

#%%
print('main.py: Running HVAC models')
start_time_initial = time.time()
for project_name in project_names:
    start_time_project = time.time()
    print('main.py: running HVAC model for ' + project_name + ' based on sizing from ' + TMY_name)
    print('main.py: creating dictionary of timeseries dataframes of all resstock sims for '+project_name)
    # construct array of all building & job IDs for the project - ResStock puts them in separate CSVs for each upgrade & the set of simulation associated w/ it
    dfResultsBaseline = pd.read_csv(path+'/'+project_name+'/inputs/ResStock_outputs/results-Baseline.csv')
    failures = dfResultsBaseline.loc[dfResultsBaseline['completed_status']!='Success','building_id'].tolist()
    dfResultsBaselineDownselect = dfResultsBaseline.loc[~dfResultsBaseline['building_id'].isin(failures)].reset_index()

    full_ids_array = (dfResultsBaselineDownselect[['job_id','building_id']].to_numpy())

    for upgrade_name in upgrade_names: # don't need to worry about excluding failures in sizing runs, HVAC_model_res catches them
        dfResultsUpgrade = pd.read_csv(path+'/'+project_name+'/inputs/ResStock_outputs/results-'+upgrade_name+'.csv')
        if failures: # check if list is empty
            # upgrades do not result in failures, so just need to locate baseline failures
            dfResultsUpgradeDownselect = dfResultsUpgrade.loc[~dfResultsUpgrade['building_id'].isin(failures)].reset_index() 
        else:
            dfResultsUpgradeDownselect = dfResultsUpgrade.reset_index()
        full_ids_array = np.vstack((full_ids_array,dfResultsUpgradeDownselect[['job_id','building_id']].to_numpy()))
    print(np.shape(full_ids_array))
    
    # before running HVAC models, create dictionary of all timeseries data to save runtime later on
    runs_dict = {}
    for i in range(0,len(full_ids_array[:,0])):
        job_id = full_ids_array[i,0]
        if job_id % 1000 == 0:
            print('job id: ' + str (job_id))
        bldg_id = full_ids_array[i,1]
        # this step is very computationally costly at scale
        dfTimeseries = pd.read_csv(path+'/'+project_name+'/inputs/ResStock_outputs/run'+str(job_id)+'/run/results_timeseries.csv').reset_index() 
        dfTimeseries = dfTimeseries.drop(0).reset_index().drop(['index','Time','TimeDST','TimeUTC'],axis=1).apply(pd.to_numeric)
        # add hourly temperature column to timeseries data as input for heat pump models
        # this reruns 4 times for each building ID, could probably be reduced
        dfTimeseries['Dry Bulb Temp (C)'] = create_temp_column(path+'/'+project_name,bldg_id,dfResultsBaselineDownselect) 

        runs_dict[str(job_id)] = dfTimeseries
    print('main.py dictionaries complete, running HVAC models: ')
    for i in upgrade_names: # run the HVAC model for every set of outputs in ResStock_outputs (ECM1, ECM2YesASHP)
        for j in sizing_logic:
            for k in backup_type:
                #print("Modeling scenario: " + i + ", Sizing: " + str(j) +", " + k)
                # eventually, loop through these
                HVAC_model_res(path+'/'+project_name,runs_dict,"/inputs/ResStock_outputs/","/res_workflow",all_sizing_dict[j+" "+i],i,j,k) 
                
    print('main.py: HVAC models for ' + project_name +' took '+str((time.time()-start_time_project)/60)+" minutes.")
print("main.py: All HVAC models took "+ str((time.time() - start_time_initial)/60) +" minutes total." )
