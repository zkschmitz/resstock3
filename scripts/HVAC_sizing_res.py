# -*- coding: utf-8 -*-
"""
Created on Sat Jun 25 11:44:31 2022

@author: Morgan Santoni-Colvin, MIT Energy Initiative
"""
import os

import numpy as np
import pandas as pd
from HVAC_model_res import (Capacity_curve_heat, COP_curve_cool,
                            COP_curve_heat, HVAC_model_res, c2f)

#from HVAC_model_res import capacity_curve_heat

#input_folder should be exact same as ResStock output, include Result-Baseline.csv, Results-Upgrade.csv (must ensure ResStock scenario is named "Upgrade"), and buildstock.csv
# current COP & capacity curve inputs are tied to prior regression analysis on NEEP datase for ASHPs with HSPF >= 11

# helper function that will be used in the main HVAC_model_res function to add the relevant temperature data to the df that the HVAC model operates on
def create_temp_column(project_path,job_id,dfResultsBaselineDownselect,dfResultsUpgradeDownselect): # job id is looped thru from dfResultsUpgrade - info on runs is most in results-baseline.csv
    building_id = dfResultsUpgradeDownselect.loc[dfResultsUpgradeDownselect['job_id']==job_id,'building_id'].values[0]
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
# def c2f(tempc):
#     tempf = tempc*9/5 + 32
#     return tempf

def HVAC_sizing_res(project_path,upgrade_name,input_folder,sizing_logic): # looping through sizing logics will happen in outer script 
    dfResultsBaseline = pd.read_csv(project_path+'/'+input_folder+'/results-Baseline.csv')
    dfResultsUpgrade = pd.read_csv(project_path+'/'+input_folder+'/results-'+upgrade_name+'.csv')
    # filters for successful runs, some ResStock buildings randomly have errors and do not produces outputs
    dfResultsBaselineDownselect = dfResultsBaseline[dfResultsBaseline['completed_status']=='Success'].reset_index()
    failures = dfResultsBaseline.loc[dfResultsBaseline['completed_status']!='Success','building_id'].tolist()
    dfResultsUpgradeDownselect = dfResultsUpgrade.loc[~dfResultsUpgrade['building_id'].isin(failures)].reset_index()

    ids_array = dfResultsUpgradeDownselect[['job_id','building_id']].to_numpy()
      
    if upgrade_name =='ECM1': #translate upgrade names from ResStock names to those used in the aggregation script later on (this is a patch for bad variable naming)
        translated = 'None'
    if upgrade_name == 'ECM2YesASHP':
        translated = 'ECM2'
    
    # for now, hard-code heating/cooling load column names as ResStock outputs them - may need to change
    heating_col_name = "Load: Heating: Delivered"
    cooling_col_name = "Load: Cooling: Delivered"
    
    
  #  def Capacity_curve_heat(tempc,sized_tempc): # output is a multiplier, it only applies if the HP is sized something less than full load.
    # Assumes linear degradation of capacity below the temperature at which sizing occurs, regardless of what that sizing temperature is
   #     tempf = c2f(tempc)
     #   sized_tempf = c2f(sized_tempc)
    #    capacitymultiplier = 1 - 0.0077*(sized_tempf-tempf) # .0077 multiplier comes from regression of NEEP capacity vs. temperature data
      #  return capacitymultiplier
    
    
    #def Capacity_curve_cool(tempc,sized_tempc): eschewing for now, cooling capacity barely varies with temperature for average model. Also need to determine what equvalent rating temperature is, if we're sizing for cooling
        
    
 ## loop through every relevant TMY timeseries file, add OAT data, run sizing
    sizing_dict = {}
    sizing_dict['failures'] = failures # to be passed through to HVAC model function, since there may be simulations in the sizing runs that may error out and need to be circumvented
    for i in range(0,len(ids_array[:,0])):
        
        job_id = ids_array[i,0]
        bldg_id = ids_array[i,1]

        dfTimeseries = pd.read_csv(project_path+'/'+input_folder+'run'+str(job_id)+'/run/results_timeseries.csv').reset_index()
        dfTimeseries=dfTimeseries.drop(0).reset_index().drop(['index','Time','TimeDST','TimeUTC'],axis=1).apply(pd.to_numeric)
        dfTimeseries['Dry Bulb Temp (C)'] = create_temp_column(project_path,job_id,dfResultsBaselineDownselect,dfResultsUpgradeDownselect)
        
        if 'Load: Cooling: Delivered' not in dfTimeseries.columns: # Catches edge case where a given ResStock building does not meet any cooling load (e.g., no AC or ventilation in the archetype)
            dfTimeseries['Load: Cooling: Delivered'] = 0
        if 'Load: Heating: Delivered' not in dfTimeseries.columns:
            dfTimeseries['Load: Heating: Delivered'] = 0

        ## determine capacity based on sizing logic. Assumption: rated heating & cooling capacity are the same. Curves are not.
        if sizing_logic == 'Winter': # size similarly to ACCA S proposed variable speed HP for heating method: 1% design temperature (1st percentile coldest temp) - method here is to take the 1% temperature and the 99% actual (not design) load (which probably don't occur in the same hour) and use those as the basis for the sizing point. Potentially results in oversizing, which is the conservative assumption when thinking of grid impacts
            capacity = dfTimeseries[heating_col_name].quantile(.99,interpolation='lower').item() # kBtu/hr, this is the max *heating* capacity at the sizing temperature
            sized_tempc = dfTimeseries['Dry Bulb Temp (C)'].quantile(.01,interpolation='lower').item() # the sizing temperature
            rated_heating_capacity = Capacity_curve_heat((47-32.2)*5/9,sized_tempc)*capacity #kBTU/hr
            rated_cooling_capacity = rated_heating_capacity
            
        if sizing_logic == 'Summer':
            rated_cooling_capacity = 1.3*dfTimeseries[cooling_col_name].quantile(.99,interpolation = 'lower').item() # # No cap degradation for cooling so rated capacity is the same as capacity at hottest temp, 85F, etc. Using NREL EUSS logic of 130% oversizing @ 99% cooling load for ducted variable speed HPs. This percentage should be more like 115% in cooling-dominated climates, may need to tweak this line when changing regions
            capacity = rated_cooling_capacity # rated cooling capacity does not change w/ temp, and max heating / max cooling capacity are equal per assumptions above
            sized_tempc = (47-32.2)*5/9 # 47F to C. assumes cooling capacity at all temps is roughly equal to rated (i.e., there is no capacity degradation in cooling mode), and that the rated capacity for cooling is the same as the rated capacity for heating (heating is rated at 47F)
        
        sizing_dict[str(bldg_id)] = (capacity,rated_cooling_capacity,sized_tempc)
    return sizing_dict