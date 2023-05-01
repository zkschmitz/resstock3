# -*- coding: utf-8 -*-
"""
Created on Tue Jul 12 20:10:35 2022

@author: Morgan Santoni-Colvin, MIT Energy Initiative
"""
## This script takes the outputs of the HVAC model that come out of main.py, takes the aggregation parameters that come out of the specified workbook in this script
# It aggregates based on equal weighting of each archetype within a given zone
# set working dir as the folder in which this script is placed
import os
path = os.getcwd()
print("PATH IS", path)

# import libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
import json
import argparse

# inputs from CLI
parser = argparse.ArgumentParser(description="Process project name and years") 
# Project name argument
parser.add_argument("project_name", type=str, help="Project name")
# Years array argument
parser.add_argument("years", nargs="+", type=str, help="Space-separated years")
args = parser.parse_args()
project_name = args.project_name
weather_list = args.years
if "TMY" in weather_list:
    weather_list.remove("TMY")

#User-defined parameters specific to each project
years_list = ['2050'] # current time horizon of the analysis, only used for selecting the proper row in the population_projections.xlsx file. Not currently useful because the buildstock & weather data are modified to reflect 2050 stock changes and climate change
# weather_list = ['2017','2018','2019'] # specify list of weather years (ints)
scenario_list = ['Hybrid_Existing','Hybrid_NoEff','HighElec_Existing','HighElec_NoEff','ReferenceEFS'] # deployment scenarios, how many heat pumps, what sizing, what backup. Each needs matching define_res_aggregation_2050_SCENARIONAME.xlsx in the main directory of the project folder
eff_scenario_names = ['None','ECM2'] # currently do not change
zones = ['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17'] # match zone specifications in dfZones. Somewhat hardcoded in current script

# import csv with household count data
dfhouseholds = pd.read_excel('population_projections.xlsx', sheet_name='Sheet1') # one needed input for weights
dfzones = pd.read_excel('NE_county_zones17.xlsx', sheet_name = 'Sheet1') # another input for weights
dfzones['FIPS'] = dfzones['FIPS'].astype(str).str.zfill(6)
dfzones['Zone'] = dfzones['Zone'].astype(str)

sizing_logic_names = ['Summer','Winter'] # same as in main.py workflow
backup_type_names = ['Existing','Electric','NoBackup'] # same as in main.py workflow
print("Python: Starting aggregation script...")

TMY_name = project_name + '_TMY'
# TMY_name = 'results_project_NE_zones17_TMY' # this block of coded literally only used to generate list of fails from sizing run and avoid them when we make dfIDs (dataframe of building/job IDs. notice this line is redundant to one we already have in the main.py workflow)

# Change the CWD to the outputs folder so that it can find the files AFTER loading the XLSX files
current_working_directory = os.getcwd()
parent_folder_path = os.path.dirname(current_working_directory)
output_directory_path = os.path.join(parent_folder_path, "outputs")
os.chdir(output_directory_path)
path = os.getcwd()
print("PATH IS", path)

all_sizing_dict = json.load(open(path+'/'+TMY_name+'/all_sizing_dict.txt')) # need to catch failures that occurreed during sizing run in this script, also
failures_TMY = all_sizing_dict['Winter ECM1']['failures'] # present work-around for getting TMY run failures into this script
    
for year in years_list: # aggregate for each time horizon + weather year + deployment scenario and save outputs as csv files in project folder
    for weather in weather_list:
        start_time = time.time()
        print('Python: running aggregation for weather year ' + weather)
        for scenario in scenario_list:
            print('Python: running aggregation for scenario ' + scenario)
            project_name_weather = project_name + "_" + weather
            print("PROJECT NAME IS ", project_name_weather)
            agg_params_workbook_name = "define_res_aggregation_2050_"+scenario+".xlsx"


            number_homes_dict = {} # really dumb way of calculating number of homes in each zone
            counties_array = dfzones['FIPS'] # FIPS is unique to each county
            for county in counties_array: # code to be robust to possibility that zones cross state lines - get weight for each county, then use this weight in the aggregations. Assumes (county population)/(state population) ratios for a given state are the same over time. Maybe worth changing to county-specific projections in the future, to the extent they exist.
                county_zone = dfzones.loc[dfzones['FIPS']==county,'Zone'].values[0] # tells us the zone the county lies in
                county_state = dfzones.loc[dfzones['FIPS']==county,'State'].values[0] # the state the county lies in
                # calculate number of households in the county 
                county_num_homes = (dfzones.loc[dfzones['FIPS']==county,'County population'].to_numpy()/(dfzones.loc[dfzones['State']==county_state,'County population'].sum()))*dfhouseholds.loc[(dfhouseholds['Year']==int(year)) & (dfhouseholds['State']==county_state) ,'Households'].to_numpy() # take total # of households in the state, multiply by the fraction of the state's population that is in the given county
                # add the number of households in the county to the number of households in the zone -- each zone's # households is sum of # households in each county within the zone
                if county_zone in number_homes_dict.keys():
                    number_homes_dict[county_zone] += county_num_homes
                else:
                    number_homes_dict[county_zone] = county_num_homes
                # should end with dictionary of {str(zone):int(num_households_in_zone)}

            #take the sample metadata (result-Baseline.csv and results-Upgrade.csv), should be in ECM1 folder
            input_folder = path+'/'+project_name_weather+'/inputs/ResStock_outputs'
            print("INPUT FOLDER IS", input_folder)

            dfResultsBaseline = pd.read_csv(input_folder+'/results-Baseline.csv')
            print(len(dfResultsBaseline))
            # filters for successful runs due to ResStock occasional random errors for a few simulations in large samples. later on we merge these with the failures in TMY/sizing run
            dfResultsBaselineDownselect = dfResultsBaseline[dfResultsBaseline['completed_status']=='Success'].reset_index()

            # dictionary would be better here, not sure I even use the ECM1 or ECM2 rows since those outputs are numbered by building ID in the res_workflow folder
            dfIDs = pd.DataFrame()
            dfIDs['building_id'] = dfResultsBaselineDownselect[~dfResultsBaselineDownselect['building_id'].isin(failures_TMY)].reset_index()['building_id'] # get set of all failures across TMY/sizing & AMY/simulation data
            building_ids = dfIDs['building_id'].astype('str').values.tolist()
            print(len(dfResultsBaselineDownselect))
            print(len(failures_TMY))
            print(len(building_ids))
            # below assumes that there are no additional failures in the upgrade runs, beyond those failures that occurred in the associated baseline runs. This seems to generally be the case
            # create dataframe of building IDs aligned with columns containing the associated job IDs in the upgrade runs, excluding the failures
            dfResultsUpgradeECM1 = pd.read_csv(input_folder+'/results-ECM1.csv')
            dfIDs['job_id_ECM1'] = dfResultsUpgradeECM1.loc[dfResultsUpgradeECM1['building_id'].astype('str').isin(building_ids)].reset_index()['job_id']
            dfResultsUpgradeECM2YesASHP = pd.read_csv(input_folder+'/results-ECM2YesASHP.csv')
            dfIDs['job_id_ECM2YesASHP'] = dfResultsUpgradeECM2YesASHP.loc[dfResultsUpgradeECM2YesASHP['building_id'].astype('str').isin(building_ids)].reset_index()['job_id']
            dfResultsUpgradeECM2NoASHP = pd.read_csv(input_folder+'/results-ECM2NoASHP.csv')
            dfIDs['job_id_ECM2NoASHP'] = dfResultsUpgradeECM2NoASHP.loc[dfResultsUpgradeECM2NoASHP['building_id'].astype('str').isin(building_ids)].reset_index()['job_id']
            dfIDs = dfIDs.astype(str)

            ## aggregate the model
            # read deploymnet fractions/probabilities from define_res_aggregation.xlsx
            dfAggASHP = pd.read_excel(path+'/'+project_name_weather+'/'+agg_params_workbook_name,sheet_name = 'ASHP')
            dfAggECM = pd.read_excel(path+'/'+project_name_weather+'/'+agg_params_workbook_name,sheet_name = 'ASHP>ECM')
            dfAggBackup = pd.read_excel(path+'/'+project_name_weather+'/'+agg_params_workbook_name,sheet_name = 'Sizing>Backup')
            dfAggSizing = pd.read_excel(path+'/'+project_name_weather+'/'+agg_params_workbook_name,sheet_name = 'ASHP>Sizing')
            
            # create list of states and counties associated with each archetype ID
            # state array isn't really necessary at this point (artifact of when we were aggregating at state rather than zonal level). But provides useful metadata for debug by giving state associated with each archetype
            state_array = dfResultsBaselineDownselect['build_existing_model.state'].append(dfResultsBaselineDownselect['build_existing_model.state']).append(dfResultsBaselineDownselect['build_existing_model.state']).reset_index(drop=True) # probably a better way to get a list and repeat it 3 times, but alas
            county_array = dfResultsBaselineDownselect['build_existing_model.county_and_puma'].str[1:7]
            # below looks like this because I don't know any easier way to take a list and append it to itself twice. we need this because there are three. structure would be something like [1,2,3,...,1,2,3,...,1,2,3,...]
            county_array = county_array.append(county_array.append(county_array)).reset_index(drop=True) # I actually don't think this is necessary any more because the for loop below would only iterate through the first third of the list (all of the building IDs once.. so only need [1,2,3,...])
            
            # find buildings that do and don't have ASHPs to begin with (in baseline/unupgraded archetypes), as these can be assigned different retrofit probabilities in the first sheet of define_res_aggregation.xlsx
            building_ids_existing_HP = dfResultsBaselineDownselect.loc[dfResultsBaselineDownselect['build_existing_model.hvac_heating_type_and_fuel']=='Electricity ASHP','building_id'].astype('str').tolist()
            building_ids_no_existing_HP = [str(x) for x in building_ids if str(x) not in building_ids_existing_HP]

            agg_data= [] # list of lists containing archetypes + retrofit package possibilities and the associated filepaths we can find the timeseries data at
            for i in range(0,len(building_ids)):
                state = state_array[i]
                county = county_array[i]
                zone = dfzones.loc[dfzones['FIPS']==county,'Zone'].astype(str)
                p_array = []

                for j in ['No ASHP', 'Yes ASHP']:
                    if building_ids[i] in building_ids_no_existing_HP:
                        pASHP = dfAggASHP.loc[dfAggASHP['Dependency1'] == 'Existing = No ASHP', 'ASHP = ' + j].to_numpy()[0]
                    elif building_ids[i] in building_ids_existing_HP:
                        pASHP = dfAggASHP.loc[dfAggASHP['Dependency1'] == 'Existing = ASHP', 'ASHP = ' + j].to_numpy()[0]

                    for k in eff_scenario_names:
                        pECM = dfAggECM.loc[dfAggECM['Dependency1'] == 'ASHP = ' + j, 'ECM = ' + k].to_numpy()[0]
                        for l in sizing_logic_names:
                            pSizing = dfAggSizing.loc[dfAggSizing['Dependency1'] == 'ASHP = '+ j, 'Sizing = '+ l].to_numpy()[0]
                            for m in backup_type_names:
                                pBackup = dfAggBackup.loc[dfAggBackup['Dependency1'] == 'Sizing = ' + l, 'Backup = ' + m].to_numpy()[0]

                                p = pASHP*pECM*pBackup*pSizing # calculate "weight" of this specific tech package in this archetype
                                p_array.append(p)
                                if j == 'Yes ASHP' and k == 'None': # sizing only applies to ASHP retrofits -- although homes with 'No ASHP' technically have sizing assigned
                                    filename = path+'/'+project_name_weather+'/res_workflow/None_'+l+'_'+m+'_HP_model_outputs_testing/modeled'+building_ids[i]+'.csv'
                                    agg_data.append([building_ids[i],state,county,zone,j,k,l,m,p,filename])
                                elif j == 'Yes ASHP' and k == 'ECM2':
                                    filename = path+'/'+project_name_weather+'/res_workflow/ECM2_'+l+'_'+m+'_HP_model_outputs_testing/modeled'+building_ids[i]+'.csv'
                                    agg_data.append([building_ids[i],state,county,zone,j,k,l,m,p,filename])
                                elif j == 'No ASHP' and k == 'None':
                                    filename = path+'/'+project_name_weather +'/inputs/ResStock_outputs/run'+building_ids[i]+'/run/results_timeseries.csv'
                                    agg_data.append([building_ids[i],state,county,zone,j,k,l,m,p,filename])
                                elif j == 'No ASHP' and k == 'ECM2':
                                    filename = path+'/'+project_name_weather +'/inputs/ResStock_outputs/run'+dfIDs.loc[dfIDs['building_id']==building_ids[i],'job_id_ECM2NoASHP'].values[0]+'/run/results_timeseries.csv'
                                    agg_data.append([building_ids[i],state,county,zone,j,k,l,m,p,filename]) # example of one retrofit package + its metadata including filename and geographic location

                if round(sum(p_array),3)!=1:
                    print('issue with weights, building ID: ' + building_ids[i] + ' ' +str(sum(p_array))) # should equal 1

            # create dataframe of all simulated building IDs and the respective weights for each ID's
            # each row corresponds to a particular combination of building ID, sizing, backup, ECM, and yes/no ASHP, plus an associated weight
            # weights should sum to 1 across the rows for a given building ID
            dfAggData = pd.DataFrame(agg_data,columns=['building_id','State','County','Zone','ASHP','ECM','Backup','Sizing','Weight','filename'])


            # list of unique states and counties that are present in the dataset -- different from states_array and county_array, which give state/county associated with each and every archetype
            states = dfResultsBaselineDownselect['build_existing_model.state'].unique() # only generating results for states that actually are represented in the data
            counties = dfResultsBaselineDownselect['build_existing_model.county_and_puma'].str[1:7].unique()
            archetype_weight_dict = {} # dictionary of weight of each archetype in a given zone -- equal to (num households in zone)/(num archetypes in zone)
            #for state in states: # old, artifact of when this was for aggregating at state level
             #   archetype_weight_dict[state] = number_homes_dict[state]/len(dfResultsBaselineDownselect[dfResultsBaselineDownselect['build_existing_model.state']==state])
              #  print(state +' weight: ' + str(archetype_weight_dict[state]))
            for zone in zones:
                counties_in_zone = dfzones.loc[dfzones['Zone']==zone,'FIPS'].to_numpy()
                num_archetypes_in_zone = len(dfResultsBaselineDownselect.loc[dfResultsBaselineDownselect['build_existing_model.county_and_puma'].str[1:7].isin(counties_in_zone)])
                print(number_homes_dict.keys())
                archetype_weight_dict[zone] = number_homes_dict[zone]/num_archetypes_in_zone
                print(zone + " num homes: " + str(number_homes_dict[zone])+" archetype weight: "+str(archetype_weight_dict[zone]) +" num archetypes: "+str(number_homes_dict[zone]/archetype_weight_dict[zone]))
            load_dict_elec = {}
            load_dict_ng = {}
            load_dict_fueloil = {}
            #for i in states:
            for i in zones:
                load_dict_elec[i] = []
                load_dict_ng[i] = []
                load_dict_fueloil[i] = []
            #print('TEST')
            # aggregate the loads. start by calculating "frankenstein" profiles for each archetype, which consists of weighted sum of retrofit package profiles where the weights sum to 1. agg profile of given retrofit package profile for given archetype = (load profile of retrofit package)*(portion of archetype represented by given retrofit package)*(archetype weight)
            for j in range(0,len(building_ids)): # for each building archetype, loop through its upgrade permutations to get its "average (frankenstein) loads", then add those to the aggregate load arrays
                #print(j)
                if j % 300 == 0 or j == 0:
                    print('Percent complete for scenario: ' + str(j/len(building_ids)*100) + ' ' + str(j) + '/' + str(len(building_ids)))
                    print('time: ' + str((time.time()-start_time)/60))
                if str(building_ids[j]) in ['9999999']: # in case manual passing around errors is needed
                    pass
                
                else:
                    dfAggReduced = dfAggData[dfAggData['building_id']==building_ids[j]].reset_index() # dfAggReduced (poorly named) is dataframe of all of the retrofit packages for a given archetype and their weights within the archetype, which sum to 1.
                    dfAggReducedDict = {}
                    for i in range(0,len(dfAggReduced)): # Iterate through retrofit packages for this archetype. load all dfs for this building ID at once to save computation time - removes 2-5 CSV reads per building ID + weight permutation compared to previous method
                        if dfAggReduced['Weight'][i] != 0:
                           # print(dfAggReduced['filename'][i])
                            dfAggReducedDict[i] = pd.read_csv(dfAggReduced['filename'][i])
                          #  if j % 300 == 0:
                           #     print(dfAggReduced['filename'][i])
                        # creating this dict may not even be necessary, can just create df on the fly in the loop below. but keeping for debug purposes - doesn't use much RAM
                    zone = dfAggReduced['Zone'].iloc[0].values[0] # Need archetype zone in order to assign the archetype + retrofit package combo load profile to the correct zone. just take the Zone of the first row, it's the same for all of the retrofit packages
                    # aggregate electricity, NG, and fuel oil consumptions for each zone. append each archetype's average/frankenstein profile to a list in a dictionary where keys are zones. then sum each list to get zone loads
                    for i in range(0,len(dfAggReduced)):
                        #print(building_ids[j])
                        if dfAggReduced['Weight'][i] == 0: # given retrofit package is not applied to this archetype, so we skip it in the aggregation to save time
                            pass
                        elif dfAggReduced.loc[i,'ASHP']=='No ASHP':
                            if 'Fuel Use: Electricity: Total' in dfAggReducedDict[i].columns:
                                elec_loads = dfAggReducedDict[i]['Fuel Use: Electricity: Total'].drop(0).to_numpy().reshape(-1,1).astype(float)
                                load_dict_elec[zone].append((np.array(elec_loads*dfAggReduced['Weight'][i]*archetype_weight_dict[zone])).astype(float))
                            else:
                                print('No electricity in this archetype! ID: ' + str(building_ids[j]))
                        elif dfAggReduced.loc[i,'ASHP']=='Yes ASHP':
                            elec_loads = dfAggReducedDict[i]['Electricity Use w/ HP (kW)'].to_numpy().reshape(-1,1) # should change this unit to kWh for consistency w/ resstock -- same number but different framing (average KW across the hour or total KWh for the hour)
                            load_dict_elec[zone].append(elec_loads*dfAggReduced['Weight'][i]*archetype_weight_dict[zone])


                    for i in range(0,len(dfAggReduced)):
                        if dfAggReduced['Weight'][i] == 0:
                            pass
                        elif dfAggReduced.loc[i,'ASHP']=='No ASHP':
                            if 'Fuel Use: Natural Gas: Total' in dfAggReducedDict[i].columns:
                                ng_loads = dfAggReducedDict[i]['Fuel Use: Natural Gas: Total'].drop(0).to_numpy().reshape(-1,1).astype(float)*.293 # in kW
                                load_dict_ng[zone].append(ng_loads*dfAggReduced['Weight'][i]*archetype_weight_dict[zone])
                        elif dfAggReduced.loc[i,'ASHP']=='Yes ASHP':
                            ng_loads = dfAggReducedDict[i]['Natural Gas Use w/ HP (kBTU)'].to_numpy().reshape(-1,1)*.293 # in kW
                            load_dict_ng[zone].append(ng_loads*dfAggReduced['Weight'][i]*archetype_weight_dict[zone])

                    for i in range(0,len(dfAggReduced)):
                        if dfAggReduced['Weight'][i] == 0:
                            pass
                        elif dfAggReduced.loc[i,'ASHP']=='No ASHP':
                            if 'Fuel Use: Fuel Oil: Total' in dfAggReducedDict[i].columns:
                                fueloil_loads = dfAggReducedDict[i]['Fuel Use: Fuel Oil: Total'].drop(0).to_numpy().reshape(-1,1).astype(float)*.293 # in kW
                                load_dict_fueloil[zone].append(fueloil_loads*dfAggReduced['Weight'][i]*archetype_weight_dict[zone])
                        elif dfAggReduced.loc[i,'ASHP']=='Yes ASHP':
                            fueloil_loads = dfAggReducedDict[i]['Fuel Oil Use w/ HP (kBTU)'].to_numpy().reshape(-1,1)*.293 # in kW
                            load_dict_fueloil[zone].append(fueloil_loads*dfAggReduced['Weight'][i]*archetype_weight_dict[zone])


            regional_electric_loads_dict = {}
            regional_ng_loads_dict = {}
            regional_fueloil_loads_dict = {}

            for i in zones:
                regional_electric_loads_dict[i] = []
                regional_ng_loads_dict[i] = []
                regional_fueloil_loads_dict[i] = []

            for i in zones:
                regional_electric_loads_dict[i] = sum(load_dict_elec[i])
                if np.isnan(np.sum(regional_electric_loads_dict[i])) == True:
                    print(str(i) + " is broken") # checking for NaNs
                else:
                    print(str(i) + ' OK') # no NaNs, dataset is whole

                regional_ng_loads_dict[i] = sum(load_dict_ng[i])
                regional_fueloil_loads_dict[i] = sum(load_dict_fueloil[i])

            for zone in zones:
                try:
                    outputdict = {
                        'Total electric load (kW)': regional_electric_loads_dict[zone].ravel(),
                        'Total NG load (kW)': regional_ng_loads_dict[zone].ravel(),
                        'Total fuel oil load (kW)': regional_fueloil_loads_dict[zone].ravel()
                        }
                    dfAggTimeSeries = pd.DataFrame(data=outputdict)
                    dfAggTimeSeries.to_csv(path+'/'+project_name_weather+'/timeseries residential outputs/timeseries_res_outputs_zone'+zone+'_'+scenario+'.csv')
                except:
                    print("FAILED FOR ZONE " + zone + " for scenario " + scenario)

            print('Aggregation complete for scenario ' + scenario +' for year' + weather)
        print("Aggregation for weather " + weather +  " took "+ str((time.time() - start_time)/60) +" minutes." )

# plt.figure()
# for state in states:
#     df = pd.read_csv(path+'/'+project_name+'/timeseries residential outputs/timeseries_res_outputs_'+state+'_'+'HighElec_Existing'+'.csv')
#     plt.plot(range(0,8760),df['Total electric load (kW)'])
