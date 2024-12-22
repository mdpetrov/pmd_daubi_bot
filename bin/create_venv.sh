#!/bin/bash

prog_path=/usr/bot/pmd_daubi_bot

sudo apt install python3.10-venv
python3 -m venv $prog_path/venv
source $prog_path/venv/bin/activate
pip install -r $prog_path/requirements.txt 