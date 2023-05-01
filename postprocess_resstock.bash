# HVAC models and aggregation
# this runs for the years indicated in the python scripts
echo "beginning python - allocating cores"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

ROOT_DIR=$PWD
PROJECT_NAME=project_remote_pjm
echo "ROOT DIR SET AS $ROOT_DIR"
years=("TMY" "2003")
OUTPUTS_DIRECTORY=/state/partition1/user/$USER
RESSTOCK_OUTPUTS_TMP_FOLDER=tmp_outputs
WEATHER_DATA_DIRECTORY=weather_data_pjm
now=$(date +"%Y-%m-%d_%H-%M-%S")

cd $ROOT_DIR/scripts

module load anaconda/2023a
echo "running main HVAC model script"
python main.py "$PROJECT_NAME" "${years[@]}"
echo "running aggregation"
python aggregate_project_res_zonal.py "$PROJECT_NAME" "${years[@]}"
echo "complete!"