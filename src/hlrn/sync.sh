#!/bin/bash

cd ../..
RSYNC_COMMAND="rsync -av src/ hlrn:/scratch/usr/bemwindl/python"

$RSYNC_COMMAND
while inotifywait -r -e close_write,modify,move,attrib,delete,create src
do
  $RSYNC_COMMAND
done