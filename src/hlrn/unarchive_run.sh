#!/bin/bash

if [ -z $RUN_NAME ]; then
  echo "RUN_NAME not set"
else
  export SRC_DIR=/scratch/usr/bemwindl/archive/$RUN_NAME
  export DEST_DIR=/scratch/usr/bemwindl/results/$RUN_NAME
fi

if [ -z $SRC_DIR ]; then
  echo "SRC_DIR not set!"
  exit 1
fi

if [ -z $DEST_DIR ]; then
  echo "DEST_DIR not set!"
  exit 1
fi

mkdir -p $DEST_DIR
cp -v $SRC_DIR/global_hparams.json $DEST_DIR/

TRIALS=$(ls $SRC_DIR | grep data)

for trial in $TRIALS
do
  mkdir -p $DEST_DIR/$trial
  cp -v $SRC_DIR/$trial/hparams.json $DEST_DIR/$trial/
  cp -v $SRC_DIR/$trial/total_progress.csv $DEST_DIR/$trial/
  cp -v $SRC_DIR/$trial/progress.csv $DEST_DIR/$trial/
  # cp -v $SRC_DIR/$trial/events* $DEST_DIR/$trial/ &
  last_itr=$(ls $SRC_DIR/$trial | grep itr_ | cut -c$(echo "itr_" | wc -c)- |  sort -g | sed 's/^/itr_/' | tail -n 1)
  cp -v $SRC_DIR/$trial/$last_itr $DEST_DIR/$trial/$last_itr &
done

wait

echo "Unarchive successful"