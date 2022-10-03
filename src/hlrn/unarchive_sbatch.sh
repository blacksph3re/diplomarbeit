#!/bin/bash

#SBATCH --nodes=1
#SBATCH --tasks-per-node=1 
#SBATCH --cpus-per-task=192
#SBATCH --hint=multithread
#SBATCH --exclusive
#SBATCH -o /scratch/usr/bemwindl/slurmlogs/archive-%j.out
#SBATCH --dependency=afterany:6227983
#SBATCH --time=2:00:00

export RUN_NAME="sac-coleman-s-3"

srun bash $SCRIPTS/unarchive_run.sh