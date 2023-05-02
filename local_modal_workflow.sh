#!/bin/bash
echo "bash script starting..."

# SETTING TOP LEVEL VARIABLES
ROOT_DIR="$PWD"
PROJECT_NAME="project_local_pjm"
echo "ROOT DIR SET AS $ROOT_DIR"
# years=("TMY" "2003")
years=("2003")
PARENT_OUTPUT_DIR="$ROOT_DIR"
RESSTOCK_OUTPUTS_TMP_FOLDER="tmp_outputs"
WEATHER_DATA_ISO="PJM"
now=$(date +"%Y-%m-%d_%H-%M-%S")

mkdir -p "${PARENT_OUTPUT_DIR}/outputs"

for year in "${years[@]}"; do
    # SETTING VARIABLES FOR ROOT DIRECTORY 
    OUTPUT_PROJECT_DIR="${PARENT_OUTPUT_DIR}/outputs/${PROJECT_NAME}_${year}"
    echo "OUTPUT_PROJECT_DIR SET AS $OUTPUT_PROJECT_DIR"

    echo "Running workflow for $year"

    # Replace weather data
    # rm -rf "${ROOT_DIR}/resources/hpxml-measures/weather"
    if [[ "$year" == "TMY" ]]; then
        echo "year is TMY. using TMY data"
    else
        echo "year is AMY, using AMY data for $year"
    fi

    # run python script to replace options tsv values
    echo "running python script to replace options tsv values"
    cd $ROOT_DIR
    python scripts/edit_options_tsv.py --ISO PJM --YEAR 2003

    # Run resstock
    cd "$ROOT_DIR"
    openstudio workflow/run_analysis.rb -y "${PROJECT_NAME}/project.yml" -k -o

    echo "resstock done, copying template"
    cd $ROOT_DIR
    cp -r output_template_folder $OUTPUT_PROJECT_DIR
    echo "template copied, copying resstock outputs to inputs folder"

    cd $PARENT_OUTPUT_DIR/outputs

    
    find "${RESSTOCK_OUTPUTS_TMP_FOLDER}" -name '*.csv' -o -name "cli_output.log" | cpio -pdm "${OUTPUT_PROJECT_DIR}/inputs"
    # use this line to copy the entire folder over for analysis
    # cp -r "${RESSTOCK_OUTPUTS_TMP_FOLDER}" "${OUTPUT_PROJECT_DIR}/inputs"

    cd $OUTPUT_PROJECT_DIR/inputs
    mv $RESSTOCK_OUTPUTS_TMP_FOLDER ResStock_outputs
    
    echo "resstock / project setup workflow complete for $year"

    # Clean up directory for outputs
    rm -rf "${PARENT_OUTPUT_DIR}/outputs/${RESSTOCK_OUTPUTS_TMP_FOLDER}"
done