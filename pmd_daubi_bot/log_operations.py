import json
import os

from . import config

path = config.path
def write_log(chat_id, text):
    with open(os.path.join(path['log_dir'], f'{chat_id}.log'), mode='a') as log_con:
        log_con.write(f'{datetime.datetime.now()}: {text}\n')