#!/bin/bash

prog_path=/usr/bot/pmd_daubi_bot
cd $prog_path
source $prog_path/venv/bin/activate

python3 setup.py install

echo "" > nohup.out
nohup $prog_path/venv/bin/python3 $prog_path/main.py >& nohup.out &
echo $!
echo $! > $prog_path/pid.nohup