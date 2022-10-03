#!/bin/bash

echo "Writing hostfile ${LOAD_BROKER_HOST_FROM_FILE:-$HOME/headnode}"
hostname | tee ${LOAD_BROKER_HOST_FROM_FILE:-$HOME/headnode}

echo "Starting broker on $(hostname)"

module load singularity
sleep 5

export BROKER_EXIT_ON_NO_WORK=1

singularity run $IMAGES/broker.sif

echo "Broker operation ended, killing slurm job"

scancel $SLURM_JOB_ID