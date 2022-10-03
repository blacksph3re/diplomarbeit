#!/bin/bash

#SBATCH -o /scratch/usr/bemwindl/slurmlogs/eval-%j.out
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870
#SBATCH hetjob
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=96
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --dependency=afterany:6392870


# for dependency, use --dependency=afterany:<jobid>


set -e

export RUN_NAME='sac-turb-optim-2'
export RUN_EVALUATION=/scratch/usr/bemwindl/results/$RUN_NAME

export AGENT_COUNT=12
export N_SAMPLE_WORKERS=8
export N_TUNE_WORKERS=10

export N_ENV_SERVERS_PER_JOB=0
export N_ENV_SERVERS_ON_AGENT_NODE=96
export N_CORES_PER_ENV_SERVER=1
export USE_HYPERTHREADING=0


export ENV_CONFIG_FILES=$(ls $EXPERIMENTS/actuator_fullturb | xargs -I{} echo "$EXPERIMENTS/actuator_fullturb/{}" | paste -sd ":" -)


export WORK=${WORK:-/scratch/usr/bemwindl}
export SCRIPTS=${SCRIPTS:-/scratch/usr/bemwindl/python/hlrn}
export IMAGES=${IMAGES:-/scratch/usr/bemwindl/images}
export PYTHON=${PYTHON:-/scratch/usr/bemwindl/python}

export LOG_DIR=$WORK/eval_logs/$RUN_NAME
export RESULT_DIR=$RUN_EVALUATION
rm -rf $LOG_DIR/*
mkdir -p $LOG_DIR

export LOAD_BROKER_HOST_FROM_FILE=$RESULT_DIR/broker_host_eval
rm -f $LOAD_BROKER_HOST_FROM_FILE


for i in $(seq 0 1 $AGENT_COUNT)
do
  AGENT_RANK=$i srun --het-group=$i bash $SCRIPTS/runagent.sh &
done


wait