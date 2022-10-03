#!/bin/bash


if [[ -z "$SLURM_JOB_ID" ]]
then
  echo "No Slurm job ID, can't start watchdog"
  exit 1
fi

echo "Starting job watchdog for $SLURM_JOB_ID on $(hostname) at $(date)"

sstat -P $SLURM_JOB_ID > $LOG_DIR/sstat.csv

while true
do
  sleep 10
  sstat -Pn $SLURM_JOB_ID >> $LOG_DIR/sstat.csv

  jobstatus=$(sacct -j $SLURM_JOB_ID)

  if [[ "$jobstatus" == *"FAILED"* ]] || [[ "$jobstatus" == *"CANCELLED"* ]]
  then
    echo "Job $SLURM_JOB_ID has FAILED was CANCELLED!"
    echo "$jobstatus"
    echo "Cancelling job immediately"
    scancel $SLURM_JOB_ID
  fi
done
