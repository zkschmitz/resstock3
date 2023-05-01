#!/bin/bash
echo "bash script starting..."

# SETTING TOP LEVEL VARIABLES
ROOT_DIR=$PWD
PROJECT_NAME=project_remote_pjm
echo "ROOT DIR SET AS $ROOT_DIR"
years=("TMY" "2003")
OUTPUTS_DIRECTORY=/state/partition1/user/$USER
RESSTOCK_OUTPUTS_TMP_FOLDER=tmp_outputs
WEATHER_DATA_DIRECTORY=weather_data_pjm
now=$(date +"%Y-%m-%d_%H-%M-%S")

# USEFUL WHEN RUNNING ON LOCAL AND WANT TO TEST
# read -p "Do you want to remove previous runs of output? (y/n) " response
# # If the user responds with 'y' or 'Y', delete the folder
# if [[ "$response" =~ ^[Yy]$ ]]; then
#     rm -rf $OUTPUTS_DIRECTORY/outputs/*
#     echo "The files have been cleaned up"
# else
#     echo "Using old output folders if they exist"
# fi
mkdir $OUTPUTS_DIRECTORY
mkdir $OUTPUTS_DIRECTORY/outputs

for year in ${years[@]}; do
    # SETTING VARIABLES FOR ROOT DIRECTORY 
    OUTPUT_PROJECT_DIR=${OUTPUTS_DIRECTORY}/outputs/${PROJECT_NAME}_${year}
    echo "OUTPUT_PROJECT_DIR SET AS $OUTPUT_PROJECT_DIR"

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
        cp -r $ROOT_DIR/$WEATHER_DATA_DIRECTORY/TMY $ROOT_DIR/resources/hpxml-measures/
        cd $ROOT_DIR/resources/hpxml-measures/
        mv TMY weather # resstock looks for EPWs in resources/hpxml-measures/weather folder
    else # copies TMY data for what I've uploaded to Supercloud
        echo "year is AMY, using AMY data for $year"
        echo "copying weather data to resources directory for resstock"
        cp -r $ROOT_DIR/$WEATHER_DATA_DIRECTORY/$year $ROOT_DIR/resources/hpxml-measures/
        cd $ROOT_DIR/resources/hpxml-measures/
        mv $year weather
    fi
    # run resstock
    cd $ROOT_DIR
    openstudio workflow/run_analysis.rb -y $PROJECT_NAME/project.yml -k -o
    
    echo "resstock done, copying template"
    cd $ROOT_DIR
    cp -r output_template_folder $OUTPUT_PROJECT_DIR
    echo "template copied, copying resstock outputs to inputs folder"
    
    cd $OUTPUTS_DIRECTORY/outputs
    find $RESSTOCK_OUTPUTS_TMP_FOLDER -name '*.csv' -o -name "cli_output.log" | cpio -pdm $OUTPUT_PROJECT_DIR/inputs

    cd $OUTPUT_PROJECT_DIR/inputs
    mv $RESSTOCK_OUTPUTS_TMP_FOLDER ResStock_outputs

    echo "copying weather data for python scripts"
    if [[ "$year" == "TMY" ]] # this is inefficient, could just directly reference weather data already in home dir rather than copying
    then
        echo "year is TMY. using TMY data" # currently copies TMY data for all locations in US, inefficient
        cp -r $ROOT_DIR/$WEATHER_DATA_DIRECTORY/TMY $OUTPUT_PROJECT_DIR/inputs/
        cd $OUTPUT_PROJECT_DIR/inputs
        mv TMY weather_res 
    else # copies TMY data for what I've uploaded to Supercloud
        echo "year is AMY, using AMY data for $year"
        cp -r $ROOT_DIR/$WEATHER_DATA_DIRECTORY/$year $OUTPUT_PROJECT_DIR/inputs/
        cd $OUTPUT_PROJECT_DIR/inputs
        mv $year weather_res
    fi

    echo "resstock / project setup workflow complete for $year"
    
    # clean up directory for outputs
    cd $OUTPUTS_DIRECTORY/outputs/
    rm -rf $RESSTOCK_OUTPUTS_TMP_FOLDER

done

# Create new folder in home directory for outputs
HOME_OUTPUT_FOLDER="$PROJECT_NAME-outputs-$now"
mkdir $HOME/resstock-outputs/$HOME_OUTPUT_FOLDER
cd $OUTPUTS_DIRECTORY
mv outputs $HOME/resstock-outputs/$HOME_OUTPUT_FOLDER

# HVAC models and aggregation
# this runs for the years indicated in the python scripts

# echo "beginning python - allocating cores"
# export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

# cd $ROOT_DIR/scripts

# module load anaconda/2023a
# echo "running main HVAC model script"
# python main.py "$PROJECT_NAME" "${years[@]}"
# echo "running aggregation"
# python aggregate_project_res_zonal.py "$PROJECT_NAME" "${years[@]}"
# echo "complete!"