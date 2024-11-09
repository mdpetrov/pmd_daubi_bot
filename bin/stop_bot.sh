#!/bin/bash

prog_path=/dev/prog/bot/pmd_daubi_bot
cd $prog_path
source $prog_path/venv/bin/activate

pid=$(cat pid.nohup)
kill -9 $pid

echo killed $pid