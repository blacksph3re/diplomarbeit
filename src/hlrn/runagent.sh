#!/bin/bash

set -e
export AGENT_RANK=${AGENT_RANK:-0}
export RUNAGENT_LOGFILE=$LOG_DIR/runagent-$AGENT_RANK.log

touch $RUNAGENT_LOGFILE
echo "Starting runagent.sh at $(date)" | tee -a $RUNAGENT_LOGFILE

if [[ -z "$LOG_DIR" ]]
then
  export LOG_DIR=$HOME/log/$SLURM_JOB_ID
  echo "Using default log dir" | tee -a $RUNAGENT_LOGFILE
fi

if [[ -z "$RESULT_DIR" ]]
then
  echo "Using default result dir" | tee -a $RUNAGENT_LOGFILE
  export RESULT_DIR=$HOME/result/$SLURM_JOB_ID
fi

mkdir -p $LOG_DIR
mkdir -p $RESULT_DIR

# We crashed the 4k limit
ulimit -u 32000

echo "Starting agent with rank $AGENT_RANK"

bash $SCRIPTS/runmonitor.sh 2>&1 | tee -a $LOG_DIR/monitor-agent-$AGENT_RANK.log &
# Start a couple of extra envs on the agent node as there's compute left to blow
N_ENV_SERVERS_PER_JOB=${N_ENV_SERVERS_ON_AGENT_NODE:-12} bash $SCRIPTS/runmultiserver.sh &

if [ "$AGENT_RANK" == "0" ]
then
  bash $SCRIPTS/runwatchdog.sh 2>&1 | tee -a $LOG_DIR/watchdog.log &

  bash $SCRIPTS/runbroker.sh 2>&1 | tee -a $LOG_DIR/broker.log &
  BROKER_PID=$!
  echo "Broker started, pid ${BROKER_PID}" | tee -a $RUNAGENT_LOGFILE
  bash $SCRIPTS/runpython.sh 2>&1 | tee -a $LOG_DIR/agent-$AGENT_RANK.log &
  AGENT_PID=$!
  echo "Agent started, pid ${AGENT_PID}" | tee -a $RUNAGENT_LOGFILE

  wait
else
  # The non-root agents are a lot simpler
  bash $SCRIPTS/runpython.sh 2>&1 | tee -a $LOG_DIR/agent-$AGENT_RANK.log
fi