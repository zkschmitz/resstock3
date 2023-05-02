import argparse
import os
import sys

import pandas as pd

parser = argparse.ArgumentParser(description="Process project ISO and year")
# Project name argument
parser.add_argument("--ISO", default='PJM', type=str, help="ISO")
# Years array argument
parser.add_argument("--YEAR", default=2003, type=int, help="Year")
args = parser.parse_args()
ISO = args.ISO
YEAR = args.YEAR


# import the options tsv file and convert to a dataframe
options_tsv_path = '/Users/zackschmitz/CODE/MIT_GenX/resstock3/resources/options_lookup.tsv'
options_df = pd.read_csv(options_tsv_path, sep='\t')

if YEAR == "TMY":
  options_df.loc[options_df['Parameter Name'] == 'County', 'Measure Arg 2'] = "weather_station_epw_filepath=../../../weather_data/{}/".format(YEAR) + options_df['Measure Arg 2'].astype(str).str[-12:]
else:
  options_df.loc[options_df['Parameter Name'] == 'County', 'Measure Arg 2'] = "weather_station_epw_filepath=../../../weather_data/{}/{}/".format(ISO, YEAR) + options_df['Measure Arg 2'].astype(str).str[-12:]

# save the dataframe as a tsv file
options_df.to_csv(options_tsv_path, sep='\t', index=False)