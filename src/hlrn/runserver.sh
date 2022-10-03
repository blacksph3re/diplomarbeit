#!/bin/bash

# Python buffers stdout - a long time
export PYTHONUNBUFFERED=1
export DISPLAY=

# Adding a random delay
random_delay=$(($RANDOM % 100))
echo "Delaying start for ${random_delay} seconds"
sleep ${random_delay}s

module load singularity


echo "Starting server at $(date) with:"
echo "OMP_NUM_THREADS:       $OMP_NUM_THREADS"
echo "OMP_PLACES:            $OMP_PLACES"
echo "OMP_PROC_BIND:         $OMP_PROC_BIND"
echo "OMP_DISPLAY_ENV:       $OMP_DISPLAY_ENV"
echo "KMP_AFFINITY:          $KMP_AFFINITY"
echo "OVERWRITE_CONFIG_FILE: $OVERWRITE_CONFIG_FILE"

export WORKING_DIR=$(TMPDIR=$LOCAL_TMPDIR mktemp -d)
#export WORKING_DIR=$(mktemp -d)
export TMPDIR=$WORKING_DIR

if [ ! -d $WORKING_DIR ]
then
  echo "Working dir $WORKING_DIR does not exist"
  exit 1
fi

# Respawn server if it exited (which it does occasionally to clean up memory leaks)
RESTART_COUNT=0
while true; do
  START_TIME=$SECONDS
  rm -rf $WORKING_DIR/*
  echo "Starting in $WORKING_DIR"
  # singularity run --contain --writable-tmpfs --workdir=$WORKING_DIR --bind $LOAD_BROKER_HOST_FROM_FILE:$LOAD_BROKER_HOST_FROM_FILE:ro --bind $WORKING_DIR $LOCAL_TMPDIR/server.sif
  singularity run --bind $WORKING_DIR --bind $OVERWRITE_CONFIG_FILE $LOCAL_TMPDIR/server.sif
  # singularity exec $IMAGES/server.sif xvfb-run -f $XVFB_FILE -a python3 /opt/scripts/server.py
  EXIT_CODE=$?

  ELAPSED=$(($SECONDS - $START_TIME))
  if (( $ELAPSED < 10 ))
  then
    RESTART_COUNT=$(($RESTART_COUNT + 1))
    echo "Server exited after only $ELAPSED seconds with code $EXIT_CODE, increasing RESTART_COUNT to $RESTART_COUNT"
  else 
    RESTART_COUNT=0
    echo "Server exited with $EXIT_CODE, restarting"
  fi

  if (( $RESTART_COUNT > 50 ))
  then
    echo "RESTART_COUNT reached $RESTART_COUNT, exiting"
    exit 1
  fi

  echo "Server exited with code $EXIT_CODE after $ELAPSED seconds, Respawning..."
  sleep $[ ( $RANDOM % 10 )  + 1 ]s
done

echo "Stopping server script"