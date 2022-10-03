#!/bin/bash

#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=192
#SBATCH --hint=multithread
#SBATCH --exclusive
#SBATCH -o /scratch/usr/bemwindl/slurmlogs/archive-%j.out
#SBATCH --dependency=afterany:6393503
#SBATCH --partition=standard96:test
#SBATCH --time=1:00:00


export RUN_NAME="sac-turb-optim-2"
export SUMMARIZE_RUN="1"
export EMPTY_SRC="1"
export UNARCHIVE_AFTER="0"

srun bash $SCRIPTS/archive_run.sh