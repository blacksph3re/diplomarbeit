#!/bin/bash

#SBATCH -o /scratch/usr/bemwindl/slurmlogs/agent-%j.out
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392869

# for dependency, use --dependency=afterany:<jobid>

set -e

export RUN_NAME='sac-turb-optim-2'

export AGENT_COUNT=12
export N_SAMPLE_WORKERS=12
export N_TUNE_WORKERS=4

export N_ENV_SERVERS_PER_JOB=0
export N_ENV_SERVERS_ON_AGENT_NODE=96
export N_CORES_PER_ENV_SERVER=1
export USE_HYPERTHREADING=0

export GRIDSEARCH_HPARAM_FILE="$EXPERIMENTS/sac-turb-optim-2.json"
export ENV_CONFIG_FILES="$EXPERIMENTS/5_turbactuatorfull.toml"

export WORK=${WORK:-/scratch/usr/bemwindl}
export SCRIPTS=${SCRIPTS:-/scratch/usr/bemwindl/python/hlrn}
export IMAGES=${IMAGES:-/scratch/usr/bemwindl/images}
export PYTHON=${PYTHON:-/scratch/usr/bemwindl/python}

export LOG_DIR=$WORK/logs/$RUN_NAME
export RESULT_DIR=$WORK/results/$RUN_NAME

rm -rf $LOG_DIR/*
#rm -rf $RESULT_DIR
#rm -rf /scratch/tmp/bemwindl/*

mkdir -p $LOG_DIR
mkdir -p $RESULT_DIR
# Tell qblade and qblade_agent to load the broker host from the headnode file
export LOAD_BROKER_HOST_FROM_FILE=$RESULT_DIR/broker_host
rm -f $LOAD_BROKER_HOST_FROM_FILE


for i in $(seq 0 1 $AGENT_COUNT)
do
  AGENT_RANK=$i srun --het-group=$i bash $SCRIPTS/runagent.sh &
done

# srun --het-group=12 bash /scratch/usr/bemwindl/tak/runtak.sh &

# srun --het-group=0 bash $SCRIPTS/runmultiserver.sh &
# srun --het-group=1 bash $SCRIPTS/runagent.sh &
# srun --het-group=2 bash $SCRIPTS/runmultiserver.sh &
# srun --het-group=3 bash $SCRIPTS/runmultiserver.sh &
# srun --het-group=4 bash $SCRIPTS/runmultiserver.sh &

wait