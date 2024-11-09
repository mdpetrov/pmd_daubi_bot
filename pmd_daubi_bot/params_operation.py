import json
import os
from time import time

def_params = {'last_time_message_sent':0,
              'last_time_message_received': time(),
              'last_ready_check':0,
              'ready_check_cd':60 * 60}

def load_params(chat_id):
    '''Load json with local parameters for the chat'''
    path = config.path
    param_dir = path['data_dir']
    param_name = f"{chat_id}.param"
    param_path = os.path.join(param_dir, param_name)
    if os.path.isfile(param_path):
        with open(param_path, 'r') as fp:
            params = json.load(fp)
        if not isinstance(params, dict):
            error_text = f'''Loaded params object has type {type(params)} instead of {type(dict)}
Debug info:
\tChat id: {chat_id}'''
# \tChat name: {chat_id} # Will be added in future
            raise TypeError(error_text)
    else:
        params = {}
        set_local_params(params)
    return params
    
def save_params(chat_id, params):
    '''Save json with local parameters for the chat'''
    if not isinstance(params, dict):
        error_text = f'''Params object has type {type(params)} instead of {type(dict)}
Debug info:
\tChat id: {chat_id}'''
# \tChat name: {chat_id} # Will be added in future
        raise TypeError(error_text)
    param_dir = config.path['data_dir']
    param_name = f"{chat_id}.param"
    param_path = os.path.join(param_dir, param_name)
    with open(param_path, 'w') as fp:
        params = json.dump(params, fp)