#!/bin/bash

prog_path="$(dirname "$(realpath "$0")")"

cd $prog_path
source $prog_path/venv/bin/activate

bin/stop_bot.sh

sleep 1

bin/start_bot.sh