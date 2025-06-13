#!/bin/bash

prog_path="$(dirname "$(realpath "$0")")"
cd $prog_path
source $prog_path/venv/bin/activate

pid=$(cat pid.nohup)
kill -9 $pid
rm pid.nohup

echo killed $pid