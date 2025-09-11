import json
import os
import time

class ParamsOperations(object):
    def __init__(self, config):
        self.def_params = {'last_time_message_sent':0,
                          'last_time_message_received': 0,
                          'last_ready_check':0,
                          'ready_check_cd':config.param_value['readycheck_cd'],
                          'phrases':{},
                          # Active Looking For Play sessions per chat
                          'lfp_sessions':{}}
        self.config = config

    def load_params(self, chat_id):
        '''Load json with local parameters for the chat'''
        path = self.config.path
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
                raise TypeError(error_text)
            params = self.check_params(params)
        else:
            params = self.def_params
        return params

    def save_params(self, chat_id, params):
        '''Save json with local parameters for the chat'''
        if not isinstance(params, dict):
            error_text = f'''Params object has type {type(params)} instead of {type(dict)}
    Debug info:
    \tChat id: {chat_id}'''
    # \tChat name: {chat_id} # Will be added in future
            raise TypeError(error_text)
        param_dir = self.config.path['data_dir']
        param_name = f"{chat_id}.param"
        param_path = os.path.join(param_dir, param_name)
        with open(param_path, 'w') as fp:
            json.dump(params, fp)
    
    def check_params(self, params):
        def_params = self.def_params
        for k,v in def_params.items():
            if k not in params.keys():
                params[k] = v
        return params