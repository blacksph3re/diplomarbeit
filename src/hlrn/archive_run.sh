#!/bin/bash

if [ -z $RUN_NAME ]; then
  echo "RUN_NAME empty!"
  exit 1
fi

SRC_DIR="$WORK/results/$RUN_NAME"
DEST_DIR="$WORK/archive/$RUN_NAME"
mkdir -p $DEST_DIR

tar -zcvf $DEST_DIR/log.tar.gz $WORK/logs/$RUN_NAME &
cp -v $SRC_DIR/global_hparams.json $DEST_DIR/
cp -v $SRC_DIR/summary.csv $DEST_DIR/

TRIALS=$(ls $SRC_DIR | grep data)

for trial in $TRIALS
do
  mkdir -p $DEST_DIR/$trial
  cp -v $SRC_DIR/$trial/hparams.json $DEST_DIR/$trial/

  # Try a relatively failsave way of merging progress.csv files
  cp -v $SRC_DIR/$trial/total_progress.csv $DEST_DIR/$trial/tmp_progress.csv || cp -v $SRC_DIR/$trial/progress.csv $DEST_DIR/$trial/tmp_progress.csv
  python $SCRIPTS/join_csv_files.py $SRC_DIR/$trial/progress.csv $DEST_DIR/$trial/tmp_progress.csv $DEST_DIR/$trial/tmp_progress.csv
  python $SCRIPTS/join_csv_files.py $DEST_DIR/$trial/total_progress.csv $DEST_DIR/$trial/tmp_progress.csv $DEST_DIR/$trial/tmp_progress.csv
  python $SCRIPTS/join_csv_files.py $DEST_DIR/$trial/progress.csv $DEST_DIR/$trial/tmp_progress.csv $DEST_DIR/$trial/tmp_progress.csv
  if [ -f "$DEST_DIR/$trial/tmp_progress.csv" ]
  then
    rm $DEST_DIR/$trial/total_progress.csv
    mv $DEST_DIR/$trial/tmp_progress.csv $DEST_DIR/$trial/total_progress.csv
  fi

  # cp -v $SRC_DIR/$trial/events* $DEST_DIR/$trial/ &
  cp -v $SRC_DIR/$trial/eval* $DEST_DIR/$trial/ &
  last_itr=$(ls -t $SRC_DIR/$trial | grep itr_ | head -n 1)
  cp -v $SRC_DIR/$trial/$last_itr $DEST_DIR/$trial/$last_itr &
done

wait

if [ "$SUMMARIZE_RUN" == "1" ]; then
  echo "Starting a summary run"
  PYTHONUNBUFFERED=1 RESULT_DIR=$DEST_DIR python $PYTHON/main/summarize.py &
fi



if [ "$EMPTY_SRC" == "1" ]; then
  eval_file_count = $(ls $SRC_DIR/data*/eval* | wc -l)
  if (( $eval_file_count < 100 )); then
    echo "Only $eval_file_count eval files found, did something go wrong? Please delete manually"
    exit 1
  fi
  
  echo "Emptying src dir"
  rm -r $SRC_DIR
fi

if [ "$UNARCHIVE_AFTER" == "1" ]; then
  echo "Unarchiving run"
  TMP_DIR=$SRC_DIR
  export SRC_DIR=$DEST_DIR
  export DEST_DIR=$TMP_DIR
  bash $SCRIPTS/unarchive_run.sh
fi

wait