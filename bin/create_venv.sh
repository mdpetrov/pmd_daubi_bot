#!/bin/bash
set -e

prog_path="$(dirname "$(realpath "$0")")"

sudo apt install python3-venv
python3 -m venv $prog_path/venv
source $prog_path/venv/bin/activate
pip install -r $prog_path/requirements.txt 