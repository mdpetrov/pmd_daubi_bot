#!/bin/bash

prog_path=/dev/prog/bot/pmd_daubi_bot
cd $prog_path
source $prog_path/venv/bin/activate

pid=$(cat pid.nohup)
kill -9 $pid

echo killed $pid

sleep 5

nohup $prog_path/venv/bin/python3 $prog_path/main.py >& nohup.out &
echo $!
echo $! > $prog_path/pid.nohup