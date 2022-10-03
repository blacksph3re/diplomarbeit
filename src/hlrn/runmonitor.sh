#!/bin/bash

echo "Starting monitor for $SLURM_JOB_ID on $(hostname) at $(date)"
mpstat 60 &
sleep 1
while true; do
  echo "-----------Usage stats at $(date) on $(hostname)---------------"
  echo "$(ps -u bemwindl | wc -l) processes running"
  free -lhw
  sleep 60
done