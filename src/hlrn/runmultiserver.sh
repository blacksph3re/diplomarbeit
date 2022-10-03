#!/bin/bash

# We actually crashed the default 4k limit :D
ulimit -u 32000

touch $LOG_DIR/multiserv-$(hostname).log
echo "Starting runmultiserver.sh at $(date)" | tee -a $LOG_DIR/multiserv-$(hostname).log

if [[ -z "$N_ENV_SERVERS_PER_JOB" ]]; then
  echo "Running multiserver.sh without job count, assuming 1" | tee -a $LOG_DIR/multiserv-$(hostname).log
  export N_ENV_SERVERS_PER_JOB=1
fi

export TOTAL_CORES="$(($N_ENV_SERVERS_PER_JOB * $N_CORES_PER_ENV_SERVER))"
if [[ $TOTAL_CORES -lt $(nproc --all) ]]; then
  echo "Not using all cores on this machine!" | tee -a $LOG_DIR/multiserv-$(hostname).log
fi

if [[ -z "$ENV_CONFIG_FILES" ]]; then
  echo "No ENV_CONFIG_FILES set, exiting!"
  exit 1
fi

IFS=':' read -r -a configfiles <<< "$ENV_CONFIG_FILES"
length_configfiles=${#configfiles[@]}

echo "Starting $N_ENV_SERVERS_PER_JOB envs with $N_CORES_PER_ENV_SERVER cores each, totalling $TOTAL_CORES, machine has $(nproc --all)" | tee -a $LOG_DIR/multiserv-$(hostname).log

bash $SCRIPTS/runmonitor.sh 2>&1 | tee $LOG_DIR/monitor-$(hostname).log &

# export WORKING_DIR=${LOCAL_TMPDIR:-$TMPDIR}
mkdir -p $LOCAL_TMPDIR
cp -v $IMAGES/server.sif $LOCAL_TMPDIR/server.sif

if [ "$USE_HYPERTHREADING" == "1" ]
then
  # Allocate with stride 2

  export OMP_NUM_THREADS=$N_CORES_PER_ENV_SERVER
  export OMP_PROC_BIND="true"
  export OMP_DISPLAY_ENV="TRUE"
  export KMP_AFFINITY=verbose,granularity=thread,compact,0,0
  for i in $(seq 0 $(($N_CORES_PER_ENV_SERVER * 2)) $(($TOTAL_CORES - 1)))
  do
    iter=$(($i / $N_CORES_PER_ENV_SERVER))

    export OVERWRITE_CONFIG_FILE=${configfiles[$(($iter % $length_configfiles))]}

    # export SERVER_WORKING_DIR=$WORKING_DIR/srv_$iter
    export OMP_PLACES="{$(seq -s, $i 2 $(($i + $N_CORES_PER_ENV_SERVER * 2 - 1)))}"
    echo "Starting $iter with $OMP_PLACES" | tee -a $LOG_DIR/multiserv-$(hostname).log
    bash $SCRIPTS/runserver.sh 2>&1 | tee $LOG_DIR/server-$(hostname)-$iter.log &

    export OVERWRITE_CONFIG_FILE=${configfiles[$((($iter + 1) % $length_configfiles))]}
    # export SERVER_WORKING_DIR=$WORKING_DIR/srv_$(($iter + 1))
    export OMP_PLACES="{$(seq -s, $(($i + 1)) 2 $(($i + $N_CORES_PER_ENV_SERVER * 2)))}"
    echo "Starting $(($iter + 1)) with $OMP_PLACES" | tee -a $LOG_DIR/multiserv-$(hostname).log
    bash $SCRIPTS/runserver.sh 2>&1 | tee $LOG_DIR/server-$(hostname)-$(($iter + 1)).log &
  done

  wait
else

  # sequential allocation without stride

  export OMP_NUM_THREADS=$N_CORES_PER_ENV_SERVER
  export OMP_PROC_BIND="true"
  export OMP_DISPLAY_ENV="TRUE"
  export KMP_AFFINITY=verbose,granularity=core,compact,0,0
  for i in $(seq 0 $N_CORES_PER_ENV_SERVER $(($TOTAL_CORES - $N_CORES_PER_ENV_SERVER)))
  do
    iter=$(($i / $N_CORES_PER_ENV_SERVER))

    export OVERWRITE_CONFIG_FILE=${configfiles[$(($iter % $length_configfiles))]}
    # export SERVER_WORKING_DIR=$WORKING_DIR/srv_$i
    export OMP_PLACES="{$i:$N_CORES_PER_ENV_SERVER}"
    bash $SCRIPTS/runserver.sh 2>&1 | tee $LOG_DIR/server-$(hostname)-${iter}.log &
  done

  wait
fi