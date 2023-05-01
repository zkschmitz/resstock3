#!/bin/bash
echo "bash script starting..."

# SETTING TOP LEVEL VARIABLES
ROOT_DIR="$PWD"
PROJECT_NAME="project_remote_pjm"
echo "ROOT DIR SET AS $ROOT_DIR"
# years=("TMY" "2003")
years=("2003")
PARENT_OUTPUT_DIR="/state/partition1/user/$USER"
RESSTOCK_OUTPUTS_TMP_FOLDER="tmp_outputs"
WEATHER_DATA_DIRECTORY="weather_data_pjm"
now=$(date +"%Y-%m-%d_%H-%M-%S")

mkdir -p "${PARENT_OUTPUT_DIR}/outputs"

for year in "${years[@]}"; do
    # SETTING VARIABLES FOR ROOT DIRECTORY 
    OUTPUT_PROJECT_DIR="${PARENT_OUTPUT_DIR}/outputs/${PROJECT_NAME}_${year}"
    echo "OUTPUT_PROJECT_DIR SET AS $OUTPUT_PROJECT_DIR"

    echo "Running workflow for $year"

    # Replace weather data
    rm -rf "${ROOT_DIR}/resources/hpxml-measures/weather"
    if [[ "$year" == "TMY" ]]; then
        echo "year is TMY. using TMY data"
    else
        echo "year is AMY, using AMY data for $year"
    fi

    cp -r "${ROOT_DIR}/${WEATHER_DATA_DIRECTORY}/${year}" "${ROOT_DIR}/resources/hpxml-measures/"
    cd "${ROOT_DIR}/resources/hpxml-measures/"
    mv "${year}" weather

    # Run resstock
    cd "$ROOT_DIR"
    openstudio workflow/run_analysis.rb -y "${PROJECT_NAME}/project.yml" -k -o

    echo "resstock done, copying template"
    cd $ROOT_DIR
    cp -r output_template_folder $OUTPUT_PROJECT_DIR
    echo "template copied, copying resstock outputs to inputs folder"

    cd $PARENT_OUTPUT_DIR/outputs

    
    # find "${RESSTOCK_OUTPUTS_TMP_FOLDER}" -name '*.csv' -o -name "cli_output.log" | cpio -pdm "${OUTPUT_PROJECT_DIR}/inputs"
    # use this line to copy the entire folder over for analysis
    cp -r "${RESSTOCK_OUTPUTS_TMP_FOLDER}" "${OUTPUT_PROJECT_DIR}/inputs"

    cd $OUTPUT_PROJECT_DIR/inputs
    mv $RESSTOCK_OUTPUTS_TMP_FOLDER ResStock_outputs
    
    echo "copying weather data for python scripts"
    cp -r "${ROOT_DIR}/${WEATHER_DATA_DIRECTORY}/${year}" "${OUTPUT_PROJECT_DIR}/inputs/"
    cd "${OUTPUT_PROJECT_DIR}/inputs"
    mv "${year}" weather_res 
    echo "resstock / project setup workflow complete for $year"

    # Clean up directory for outputs
    # rm -rf "${PARENT_OUTPUT_DIR}/outputs/${RESSTOCK_OUTPUTS_TMP_FOLDER}"
done

# Create new folder in home directory for outputs
HOME_OUTPUT_FOLDER="pjm-${now}"
mkdir -p "$HOME/resstock-outputs/${HOME_OUTPUT_FOLDER}"
cd $PARENT_OUTPUT_DIR
mv outputs "$HOME/resstock-outputs/${HOME_OUTPUT_FOLDER}"


# HVAC models and aggregation
# echo "beginning python - allocating cores"
# export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

# cd $ROOT_DIR/scripts

# module load anaconda/2023a
# echo "running main HVAC model script"
# python main.py "$PROJECT_NAME" "${years[@]}"
# echo "running aggregation"
# python aggregate_project_res_zonal.py "$PROJECT_NAME" "${years[@]}"
# echo "complete!"

