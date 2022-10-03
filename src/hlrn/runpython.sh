#!/bin/bash
echo "Starting runpython.sh at $(date)"

set -e

module load anaconda3
source $HOME/.bashrc
conda activate rl

cd $PYTHON/main

# Python buffers stdout - a long time
export PYTHONUNBUFFERED=1
export TF_CPP_MIN_LOG_LEVEL='2' 

if [ -z $RUN_EVALUATION ]
then
  echo "Starting run_gridsearch.py"
  python run_gridsearch.py
else
  echo "Starting run_evaluation.py"
  python run_evaluation.py
fi