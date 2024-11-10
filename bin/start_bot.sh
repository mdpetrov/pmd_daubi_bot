#!/bin/bash

prog_path=/dev/prog/bot/pmd_daubi_bot
cd $prog_path
source $prog_path/venv/bin/activate

python3 setup.py install

nohup $prog_path/venv/bin/python3 $prog_path/main.py &
echo $! > $prog_path/pid.nohup