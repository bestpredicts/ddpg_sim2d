#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo $DIR
export PYTHONPATH=$PYTHONPATH:$DIR/..
HFO_mgm/bin/HFO --fullstate --no-logging --headless --defense-agents=$1 --offense-npcs=1 --defense-npcs=1 --offense-team=$2 --defense-team=$3 --trials $4 &
sleep 5
# Sleep is needed to make sure doesn't get connected too soon, as unum 1 (goalie)
python ./agents/agent1.py $3 $1&
sleep 1
# python ./agents/agent.py $2&
# sleep 1
# python ./agents/agent.py $2&
# sleep 1
# python ./agents/agent.py $2&
# sleep 1
# # python ./agents/agent.py $2&
# sleep 1
# The magic line
#   $$ holds the PID for this script
#   Negation means kill by process group id instead of PID
trap "kill -TERM -$$" SIGINT
wait