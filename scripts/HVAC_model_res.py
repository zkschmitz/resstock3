# -*- coding: utf-8 -*-
"""
Created on Sat Jun 25 11:44:31 2022

@author: Morgan Santoni-Colvin, MIT Energy Initiative
"""
import pandas as pd
import numpy as np
import os
import shutil

#define functions for capacity, COP curves based on NEEP CC-ASHP data.
def COP_curve_heat(tempc): # temp in units of C, curve in units of F
    tempf = c2f(tempc)
    COPheat = .025*tempf + 1.93
    return COPheat

def Capacity_curve_heat(tempc,sized_tempc): # output is a multiplier, it only applies if the HP is sized something less than full load.
# Assumes linear degradation of capacity below the temperature at which sizing occurs, regardless of what that sizing temperature is
    tempf = c2f(tempc)
    sized_tempf = c2f(sized_tempc)
    capacitymultiplier = 1 - 0.0085*(sized_tempf-tempf) # .0077 multiplier comes from regression of NEEP capacity vs. temperature data
    return capacitymultiplier

def COP_curve_cool(tempc):
    tempf = c2f(tempc)
    COPcool = -.065*tempf + 9.42 # from NEEP data
    return COPcool

#input_folder should be exact same as ResStock output, include Result-Baseline.csv, Results-Upgrade.csv (must ensure ResStock scenario is named "Upgrade"), and buildstock.csv
# current COP & capacity curve inputs are tied to prior regression analysis on NEEP datase for ASHPs with HSPF >= 11

# helper function that will be used in the main HVAC_model_res function to add the relevant temperature data to the df that the HVAC model operates on
def create_temp_column(project_path,building_id,dfResultsBaselineDownselect): # job id is looped thru from dfResultsUpgrade - info on runs is most in results-baseline.csv
    weather_FIP = dfResultsBaselineDownselect.loc[dfResultsBaselineDownselect['building_id']==building_id,'build_existing_model.county_and_puma'].values[0].split(',')[0] # weather file city name is only in baseline csv output   
    dfweather = pd.read_csv(project_path+'/inputs/weather_res/'+weather_FIP+'.epw',skiprows=8,delimiter = ",",header=None)
    #print(weather_FIP)
    
    if len(dfweather.columns)==1: # some EPWs don't load in properly w/ comma delimiters and are one big string, so this is a brute-force workaround
        dfweather = pd.DataFrame(dfweather[0].str.split(',').tolist())
        dfdrybulbs = dfweather[dfweather.columns[6]].astype('float32')
    else: # if file is normal
        dfdrybulbs = dfweather[dfweather.columns[6]]
    return dfdrybulbs

# temperature converter for when its needed in the script (weather data is in C, but heat pump performance curves are in F)
def c2f(tempc):
    tempf = tempc*9/5 + 32
    return tempf

def HVAC_model_res(project_path,runs_dict,input_folder,output_folder,sizing_dict,upgrade_name,sizing_logic,backup_type): # looping through sizing logics will happen in outer script 
    dfResultsBaseline = pd.read_csv(project_path+'/'+input_folder+'/results-Baseline.csv')
    dfResultsUpgrade = pd.read_csv(project_path+'/'+input_folder+'/results-'+upgrade_name+'.csv')
    # filters for successful runs, some ResStock buildings randomly have errors and do not produces outputs
    dfResultsBaselineDownselect = dfResultsBaseline[dfResultsBaseline['completed_status']=='Success'].reset_index()
    failures = dfResultsBaseline.loc[dfResultsBaseline['completed_status']!='Success','building_id'].tolist()
    #print(failures)
    #print(sizing_dict['failures'])
    failures.extend(sizing_dict['failures']) # seems like TMY/sizing and AMY/performance runs usually have the same buildings fail, but not always the case. So catch both
    #print(failures)
    if failures: # check if there is anything in the list. usually there is
        dfResultsUpgradeDownselect = dfResultsUpgrade.loc[~dfResultsUpgrade['building_id'].isin(failures)].reset_index() # upgrades do not result in failures, so just need to locate baseline failures
        print('yes failures')
        print(failures)
    else:
        print('no failures')
        dfResultsUpgradeDownselect = dfResultsUpgrade.reset_index()
    # we will add these to each timeseries file corresponding to each HVAC model run, as we generate them for each building / sizing method
    ids_array = dfResultsUpgradeDownselect[['job_id','building_id']].to_numpy()
    #print(ids_array[150:])
      
    if upgrade_name =='ECM1': #translate upgrade names from ResStock names to those used in the aggregation script later on (this is a patch for bad variable naming)
        translated = 'None'
    if upgrade_name == 'ECM2YesASHP':
        translated = 'ECM2'
    
    # create new folder in res_workflow for CSVs that will contain fuel loads for this specific retrofit package for all archetypes
    folder_path = project_path+'/'+output_folder+'/'+translated+'_'+str(sizing_logic)+'_'+backup_type+'_HP_model_outputs_testing'
    if os.path.exists(folder_path):
        if os.path.isdir(folder_path):
            # folder exists and is a directory
            print(f"Deleting folder: {folder_path}")
            # os.rmdir(folder_path)
            shutil.rmtree(folder_path)
    os.makedirs(folder_path)
    
    # for now, hard-code heating/cooling load column names as ResStock outputs them - may need to change
    heating_col_name = "Load: Heating: Delivered"
    cooling_col_name = "Load: Cooling: Delivered"
    
    
    #def Capacity_curve_cool(tempc,sized_tempc): eschewing for now, cooling capacity barely varies with temperature for average model. Also need to determine what equvalent rating temperature is, if we're sizing for cooling
        
        
    #backup heating logic: efficiency is tied to the efficiency specified in the Results_Baseline column "build_existing_model.hvac_heating_efficiency"
    #some systems are assigned an efficiency of zero, i.e. we act as if there is no backup if there is already a ASHP in place or if the system type is unknown
    # existing ASHP efficiencies currently don't matter because they aren't given retrofits in the aggregation model
    backup_eff_dict = {"Fuel Furnace, 60% AFUE":.60, "Fuel Furnace, 76% AFUE":.76, "Fuel Furnace, 80% AFUE":.80, "Fuel Boiler, 76% AFUE":.76, "Fuel Boiler, 80% AFUE":.80,"Fuel Boiler, 90% AFUE":.90, "Fuel Furnace, 92.5% AFUE":.925, "Fuel Wall/Floor Furnace, 60% AFUE":.60, "Fuel Wall/Floor Furnace, 68% AFUE":.68, "Electric Boiler, 100% AFUE": 1,"Shared Heating":.8, "Electric Baseboard, 100% Efficiency":1, "ASHP, SEER 15, 8.5 HSPF":0,"Electric Furnace, 100% AFUE":1, 'ASHP, SEER 13, 7.7 HSPF':0, 'ASHP, SEER 10, 6.2 HSPF':0,'Other':0,'None':0,'Electric Wall Furnace, 100% AFUE':1}
    
 ## loop through every relevant timeseries files already saved to dictionary in main.py (including loads and OAT data), run HVAC model
    
    for i in range(0,len(ids_array[:,0])):
        job_id = ids_array[i,0]
        bldg_id = ids_array[i,1]
        #print("Building ID: " + str(bldg_id) + " Job ID: " + str(job_id))
       # dfTimeseries = pd.read_csv(input_folder+'run'+str(job_id)+'/run/results_timeseries.csv').reset_index() # this step is very computationally costly at scale
        #dfTimeseries=dfTimeseries.drop(0).reset_index().drop(['index','Time','TimeDST','TimeUTC'],axis=1).apply(pd.to_numeric)
        #dfTimeseries['Dry Bulb Temp (C)'] = create_temp_column(project_path,job_id,dfResultsBaselineDownselect,dfResultsUpgradeDownselect)
        #print(len(dfTimeseries['Dry Bulb Temp (C)'].index))
        dfTimeseries = runs_dict[str(job_id)]
        
        if 'Load: Cooling: Delivered' not in dfTimeseries.columns:
            dfTimeseries['Load: Cooling: Delivered'] = 0
        if 'Load: Heating: Delivered' not in dfTimeseries.columns:
            dfTimeseries['Load: Heating: Delivered'] = 0
        if "End Use: Electricity: Cooling" not in dfTimeseries.columns:
            dfTimeseries['End Use: Electricity: Cooling'] = 0
        # run HVAC model
        # heating
        ## determine capacity based on sizing logic.
        capacity = sizing_dict[str(bldg_id)][0]
        rated_cooling_capacity = sizing_dict[str(bldg_id)][1]
        sized_tempc = sizing_dict[str(bldg_id)][2]
        
        
        # all of the below applies only to heating            
        dfTimeseries['Capacity multiplier'] = Capacity_curve_heat(dfTimeseries['Dry Bulb Temp (C)'],sized_tempc) # for heating
        dfTimeseries['Capacity @ temp'] = dfTimeseries['Capacity multiplier']*capacity # in kBTU/hr
        dfTimeseries['Heating COP'] = COP_curve_heat(dfTimeseries['Dry Bulb Temp (C)'])
        
        #Backup heating logic
        dfTimeseries['Unmet heating load (kBTU)'] = np.where(dfTimeseries['Capacity @ temp'] < dfTimeseries[heating_col_name], dfTimeseries[heating_col_name]-dfTimeseries['Capacity @ temp'], 0) # in kbtu/hr
        if backup_type == 'Existing': # use existing system
            backup_eff = backup_eff_dict[str(dfResultsBaselineDownselect.loc[dfResultsBaselineDownselect['building_id'] == bldg_id, 'build_existing_model.hvac_heating_efficiency'].iloc[0])]
            backup_fuel = dfResultsBaselineDownselect.loc[dfResultsBaselineDownselect['building_id'] == bldg_id, 'build_existing_model.heating_fuel'].iloc[0]            
            
        if backup_type == 'Electric': #override existing system, backup is electric resistance
            backup_eff = 1
            backup_fuel = 'Electricity'
        
        if backup_type == 'NoBackup':
            backup_eff = 0
            backup_fuel = 'Electricity' # placeholder, really there isn't a backup fuel type at all if there's no backup. doesn't affect the calculations
            
     # if ducted and has NG/fuel oil backup, we need a switchover temperature. This is because an ASHP cannot be placed on the same duct downstream of a forced air system, which is what we would expect if we added one to an existing non-electric system. This follows NREL EUSS assumptions.
        if sizing_logic == 'Winter':
            switchover_temp = -12.2 # 10F in C, our assumed switchover temp for winter
        if sizing_logic == 'Summer':  # 41F in C, same as NREL EUSS assumption for "minimum efficiency retrofit"
            switchover_temp = 5
        if backup_fuel != 'Electricity' and dfResultsBaselineDownselect.loc[dfResultsBaselineDownselect['building_id']==bldg_id,'build_existing_model.hvac_has_ducts'].values[0] == 'Yes': # note that in Summer-sized systems w/ no backup in cold climates, we get bad but predictable outcome => building won't meet load. Even worse, in ducted systems, below switchoff temp we get zero heat supplied. NEVER run this scenario because it doesn't make sense.
            dfTimeseries['HP Electricity: Heating (kW)'] = (dfTimeseries['Load: Heating: Delivered'] - dfTimeseries['Unmet heating load (kBTU)'])/COP_curve_heat(dfTimeseries['Dry Bulb Temp (C)'])*.293 # note that if not meeting load above switchover temp, load is simply not met. we'd expect unmet load = 0 for all/most of these rows if HP is sized properly
            # overwrite rows below the cutoff temp such that all of the load is being met by the backup below switchoff temp -> HP consumption = 0, unmet load is equal to total load
            dfTimeseries.loc[dfTimeseries['Dry Bulb Temp (C)'] < switchover_temp,'HP Electricity: Heating (kW)'] = 0 # HP doesn't run below cutoff temp
            dfTimeseries.loc[dfTimeseries['Dry Bulb Temp (C)'] < switchover_temp,'Unmet heating load (kBTU)'] = dfTimeseries.loc[dfTimeseries['Dry Bulb Temp (C)'] < switchover_temp,'Load: Heating: Delivered'] # when below switchover temp, HP meets none of the load (it is turned off). All load is unmet and picked up by backup system
            if backup_eff > 0:
                dfTimeseries['Backup Heating: '+ backup_fuel] = 0 # generate column for backup heating, overwrite rows where backup heat is actually on (temp is below cutoff)
                dfTimeseries.loc[dfTimeseries['Dry Bulb Temp (C)'] < switchover_temp,'Backup Heating: '+ backup_fuel] = dfTimeseries.loc[dfTimeseries['Dry Bulb Temp (C)'] < switchover_temp,'Unmet heating load (kBTU)']/backup_eff # in kBTU, backup only runs below cutoff temp
            else:
                dfTimeseries['Backup Heating: '+ backup_fuel] = 0
        else: # run backup as auxiliary heat - HP and backup can run concurrently, backup always picks up the unmet load. Note that this condition always applies for electric backup, which we assume is installed downstream of the HP even in existing ducting, or as baseboard etc. in a non-ducted system.
            dfTimeseries['HP Electricity: Heating (kW)'] = (dfTimeseries['Load: Heating: Delivered'] - dfTimeseries['Unmet heating load (kBTU)'])/COP_curve_heat(dfTimeseries['Dry Bulb Temp (C)'])*.293 # convert from kBTU/hr to kW        
            if backup_eff > 0: 
                dfTimeseries['Backup Heating: '+ backup_fuel] = dfTimeseries['Unmet heating load (kBTU)']/backup_eff # in kbtu/hr, assumes backup is sized to meet entirety of load not met by HP
            else:
                dfTimeseries['Backup Heating: '+ backup_fuel] = 0 # there are certain cases where no backup is assigned - a few ResStock systems do not lend themselves to fuel type / efficiencies (see dictionary above). So some buildings will underestimate electricity load particularly summer-sized. Only a problem for "other" and "None" as buildings with ASHPs already in them do not get retrofitted in the current model aggregation. Only a small number of these
        
        
        #cooling       
        dfTimeseries['Cooling COP'] = COP_curve_cool(dfTimeseries['Dry Bulb Temp (C)'])
        dfTimeseries['HP Electricity: Cooling (kW)'] = 0 # initialize column
        # if cooling capacity cannot be met, then heat pump / AC is running all-out. Code does not record when this occurs, so must be wary of it. In warmer climates, its possible that when we size for winter/heating, we are not sizing sufficiently for summer/cooling
        # we do not model temperature-dependent cooling capacity degradation (its fairly negligible based on NEEP data)
        dfTimeseries.loc[dfTimeseries['Load: Cooling: Delivered']<rated_cooling_capacity,'HP Electricity: Cooling (kW)'] = dfTimeseries['Load: Cooling: Delivered']/dfTimeseries['Cooling COP']*.293 #kBTU to kW
        dfTimeseries.loc[dfTimeseries['Load: Cooling: Delivered']>=rated_cooling_capacity,'HP Electricity: Cooling (kW)'] = rated_cooling_capacity/dfTimeseries['Cooling COP']*.293 #, assumes cooling cap is not temp-dependent/derated
        
        # ResStock does not report a "Fuel Use" column for a given fuel if it does not exist in the home. Add them to all files for consistency
        # similarly for heating (need this column to determine fuel use related to backup heating under presence of HP install)
        for fuel in ['Electricity','Fuel Oil','Natural Gas']:
            if 'Fuel Use: ' + fuel + ': Total' not in dfTimeseries.columns:
                dfTimeseries['Fuel Use: ' + fuel + ': Total'] = 0
            if 'Fuel Use: ' + fuel + ': Heating' not in dfTimeseries.columns:
                dfTimeseries['End Use: ' + fuel + ': Heating'] = 0
        
        #determine electricity loads with added HP loads as well as new loads for fossil fuels if present
        if 'End Use: Electricity: Heating Heat Pump Backup' in dfTimeseries.columns:# it seems like some buildings do not have backup sized in ResStock -- maybe if low load, ResStock doesn't size for it?
            if backup_fuel == 'Electricity':
                dfTimeseries['Electricity Use w/ HP (kW)'] = dfTimeseries['Fuel Use: Electricity: Total'] - dfTimeseries['End Use: Electricity: Cooling'] - dfTimeseries['End Use: Electricity: Heating'] - dfTimeseries['End Use: Electricity: Heating Heat Pump Backup'] + dfTimeseries['HP Electricity: Cooling (kW)'] + dfTimeseries['HP Electricity: Heating (kW)'] + dfTimeseries['Backup Heating: '+ backup_fuel]*.293 # in kW -- backup heating is in kBTU so needs conversion
            if backup_fuel == 'Natural Gas':
                dfTimeseries['Electricity Use w/ HP (kW)'] = dfTimeseries['Fuel Use: Electricity: Total'] - dfTimeseries['End Use: Electricity: Cooling'] - dfTimeseries['End Use: Electricity: Heating'] - dfTimeseries['End Use: Electricity: Heating Heat Pump Backup'] + dfTimeseries['HP Electricity: Cooling (kW)'] + dfTimeseries['HP Electricity: Heating (kW)'] # in kW
                dfTimeseries['Natural Gas Use w/ HP (kBTU)'] = dfTimeseries['Fuel Use: Natural Gas: Total'] - dfTimeseries['End Use: Natural Gas: Heating'] + dfTimeseries['Backup Heating: '+ backup_fuel]
            
            if backup_fuel == 'Fuel Oil':
                dfTimeseries['Electricity Use w/ HP (kW)'] = dfTimeseries['Fuel Use: Electricity: Total'] - dfTimeseries['End Use: Electricity: Cooling'] - dfTimeseries['End Use: Electricity: Heating'] - dfTimeseries['End Use: Electricity: Heating Heat Pump Backup'] + dfTimeseries['HP Electricity: Cooling (kW)'] + dfTimeseries['HP Electricity: Heating (kW)'] # in kW
                dfTimeseries['Fuel Oil Use w/ HP (kBTU)'] = dfTimeseries['Fuel Use: Fuel Oil: Total'] - dfTimeseries['End Use: Fuel Oil: Heating'] + dfTimeseries['Backup Heating: '+ backup_fuel]
            else: # for other fuels, we don't count the usage at the moment - propane etc. are small
                dfTimeseries['Electricity Use w/ HP (kW)'] = dfTimeseries['Fuel Use: Electricity: Total'] - dfTimeseries['End Use: Electricity: Cooling'] - dfTimeseries['End Use: Electricity: Heating'] - dfTimeseries['End Use: Electricity: Heating Heat Pump Backup'] + dfTimeseries['HP Electricity: Cooling (kW)'] + dfTimeseries['HP Electricity: Heating (kW)'] # in kW
        else:
            if backup_fuel == 'Electricity':
                dfTimeseries['Electricity Use w/ HP (kW)'] = dfTimeseries['Fuel Use: Electricity: Total'] - dfTimeseries['End Use: Electricity: Cooling'] - dfTimeseries['End Use: Electricity: Heating'] + dfTimeseries['HP Electricity: Cooling (kW)'] + dfTimeseries['HP Electricity: Heating (kW)'] + dfTimeseries['Backup Heating: '+ backup_fuel]*.293 # in kW
            
            if backup_fuel == 'Natural Gas':
                dfTimeseries['Electricity Use w/ HP (kW)'] = dfTimeseries['Fuel Use: Electricity: Total'] - dfTimeseries['End Use: Electricity: Cooling'] - dfTimeseries['End Use: Electricity: Heating'] + dfTimeseries['HP Electricity: Cooling (kW)'] + dfTimeseries['HP Electricity: Heating (kW)'] # in kW
                dfTimeseries['Natural Gas Use w/ HP (kBTU)'] = dfTimeseries['Fuel Use: Natural Gas: Total'] - dfTimeseries['End Use: Natural Gas: Heating'] + dfTimeseries['Backup Heating: '+ backup_fuel]
            
            if backup_fuel == 'Fuel Oil':
                dfTimeseries['Electricity Use w/ HP (kW)'] = dfTimeseries['Fuel Use: Electricity: Total'] - dfTimeseries['End Use: Electricity: Cooling'] - dfTimeseries['End Use: Electricity: Heating'] + dfTimeseries['HP Electricity: Cooling (kW)'] + dfTimeseries['HP Electricity: Heating (kW)'] # in kW
                dfTimeseries['Fuel Oil Use w/ HP (kBTU)'] = dfTimeseries['Fuel Use: Fuel Oil: Total'] - dfTimeseries['End Use: Fuel Oil: Heating'] + dfTimeseries['Backup Heating: '+ backup_fuel]
            else:
                dfTimeseries['Electricity Use w/ HP (kW)'] = dfTimeseries['Fuel Use: Electricity: Total'] - dfTimeseries['End Use: Electricity: Cooling'] - dfTimeseries['End Use: Electricity: Heating'] + dfTimeseries['HP Electricity: Cooling (kW)'] + dfTimeseries['HP Electricity: Heating (kW)'] # in kW
        
        #again, add all fuel columns for consistency
        if 'Electricity Use w/ HP (kW)' not in dfTimeseries.columns:
            dfTimeseries['Electricity Use w/ HP (kW)'] = dfTimeseries['Fuel Use: Electricity: Total']
        if 'Fuel Oil Use w/ HP (kBTU)' not in dfTimeseries.columns:
            dfTimeseries['Fuel Oil Use w/ HP (kBTU)'] = dfTimeseries['Fuel Use: Fuel Oil: Total']
        if 'Natural Gas Use w/ HP (kBTU)' not in dfTimeseries.columns:
            dfTimeseries['Natural Gas Use w/ HP (kBTU)'] = dfTimeseries['Fuel Use: Natural Gas: Total']
            
            
        # The below code removes all columns besides the end-uses, to reduce file output size and runtime of writing to CSV. If ever need to debug HP model code, should comment this out, rerun, and look at results.
        #dfTimeseries = dfTimeseries[['Electricity Use w/ HP (kW)','Fuel Oil Use w/ HP (kBTU)','Natural Gas Use w/ HP (kBTU)','Unmet heating load (kBTU)','HP Electricity: Heating (kW)','HP Electricity: Cooling (kW)','Dry Bulb Temp (C)','Cooling COP','Load: Cooling: Delivered','Load: Heating: Delivered','Backup Heating: '+ backup_fuel]]
        dfTimeseries = dfTimeseries[['Electricity Use w/ HP (kW)','Fuel Oil Use w/ HP (kBTU)','Natural Gas Use w/ HP (kBTU)']]


        dfTimeseries.to_csv(project_path+'/'+output_folder+'/'+translated+'_'+str(sizing_logic)+'_'+backup_type+'_HP_model_outputs_testing/modeled'+str(bldg_id)+'.csv',sep=',',encoding='utf-8', index=False)