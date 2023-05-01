#!/bin/bash
echo "bash script starting..."

# SETTING TOP LEVEL VARIABLES
ROOT_DIR=$PWD
PROJECT_NAME=project_local_mass
echo "ROOT DIR SET AS $ROOT_DIR"
years=("TMY" "2011")

read -p "Do you want to remove previous runs of output? (y/n) " response
# If the user responds with 'y' or 'Y', delete the folder
if [[ "$response" =~ ^[Yy]$ ]]; then
    rm -rf $ROOT_DIR/outputs/*
    echo "The files have been cleaned up"
else
    echo "Using old output folders if they exist"
fi

for year in ${years[@]}; do
    # SETTING VARIABLES FOR ROOT DIRECTORY 
    OUTPUT_PROJECT_DIR=${ROOT_DIR}/outputs/${PROJECT_NAME}_${year}
    echo "OUTPUT_PROJECT_DIR SET AS $OUTPUT_PROJECT_DIR"

    if [ -d "$OUTPUT_PROJECT_DIR" ] && [ "$(ls -A "$OUTPUT_PROJECT_DIR")" ]; then
        echo "The folder exists and is not empty."
    else
        echo "The folder does not exist or is empty."
        echo "Running workflow for $year"
        ### for each year:
        # START WITH WEATHER FOLDER IN HPXML FOLDER, then replace weather data with appropriate folder of morphed located in #HOME/testing/weather_2050_YEAR
        ## Year: $year
        # replace weather data
        ! rm -rf $ROOT_DIR/resources/hpxml-measures/weather # may be computationally expensive and not useful?
        if [[ "$year" == "TMY" ]]
        then
            echo "year is TMY. using TMY data" # currently copies TMY data for all locations in US, inefficient
            echo "copying weather data to resources directory for resstock"
            cp -r $ROOT_DIR/weather_data/TMY $ROOT_DIR/resources/hpxml-measures/
            cd $ROOT_DIR/resources/hpxml-measures/
            mv TMY weather # resstock looks for EPWs in resources/hpxml-measures/weather folder
        else # copies TMY data for what I've uploaded to Supercloud
            echo "year is AMY, using AMY data for $year"
            echo "copying weather data to resources directory for resstock"
            cp -r $ROOT_DIR/weather_data/$year $ROOT_DIR/resources/hpxml-measures/
            cd $ROOT_DIR/resources/hpxml-measures/
            mv $year weather
        fi
        # run resstock
        cd $ROOT_DIR
        openstudio workflow/run_analysis.rb -y project_local_mass/local_mass.yml -k -o
        
        echo "resstock done, copying template"
        cd $ROOT_DIR
        cp -r output_template_folder $ROOT_DIR/outputs/${PROJECT_NAME}_$year
        echo "template copied, copying resstock outputs to inputs folder"
        
        cd $ROOT_DIR/outputs
        find local_mass -name '*.csv' -o -name "cli_output.log" | cpio -pdm $OUTPUT_PROJECT_DIR/inputs

        cd $OUTPUT_PROJECT_DIR/inputs
        mv local_mass ResStock_outputs

        echo "copying weather data for python scripts"
        if [[ "$year" == "TMY" ]] # this is inefficient, could just directly reference weather data already in home dir rather than copying
        then
            echo "year is TMY. using TMY data" # currently copies TMY data for all locations in US, inefficient
            cp -r $ROOT_DIR/weather_data/TMY $OUTPUT_PROJECT_DIR/inputs/
            cd $OUTPUT_PROJECT_DIR/inputs
            mv TMY weather_res 
        else # copies TMY data for what I've uploaded to Supercloud
            echo "year is AMY, using AMY data for $year"
            cp -r $ROOT_DIR/weather_data/$year $OUTPUT_PROJECT_DIR/inputs/
            cd $OUTPUT_PROJECT_DIR/inputs
            mv $year weather_res
        fi

        echo "resstock / project setup workflow complete for $year"
        
        # clean up directory for outputs
        cd $ROOT_DIR/outputs/
        rm -rf local_mass
    fi

done


# HVAC models and aggregation
# this runs for the years indicated in the python scripts
# echo "beginning python - allocating cores"
# export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

cd $ROOT_DIR/scripts

# module load anaconda/2020b
echo "running main HVAC model script"
python main.py "$PROJECT_NAME" "${years[@]}"
echo "running aggregation"
python aggregate_project_res_zonal.py "$PROJECT_NAME" "${years[@]}"
echo "complete!"