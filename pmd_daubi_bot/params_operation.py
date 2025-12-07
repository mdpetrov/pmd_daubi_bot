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
    
    def load_user_params(self, user_id):
        '''Load json with user-specific parameters'''
        path = self.config.path
        param_dir = path['data_dir']
        param_name = f"{user_id}.param"
        param_path = os.path.join(param_dir, param_name)
        if os.path.isfile(param_path):
            with open(param_path, 'r') as fp:
                user_params = json.load(fp)
            if not isinstance(user_params, dict):
                error_text = f'''Loaded user params object has type {type(user_params)} instead of {type(dict)}
                                    Debug info:
                                    \tUser id: {user_id}'''
                raise TypeError(error_text)
            # Ensure chat_ids list exists
            if 'chat_ids' not in user_params:
                user_params['chat_ids'] = []
        else:
            user_params = {'chat_ids': []}
        return user_params
    
    def save_user_params(self, user_id, user_params):
        '''Save json with user-specific parameters'''
        if not isinstance(user_params, dict):
            error_text = f'''User params object has type {type(user_params)} instead of {type(dict)}
    Debug info:
    \tUser id: {user_id}'''
            raise TypeError(error_text)
        param_dir = self.config.path['data_dir']
        param_name = f"{user_id}.param"
        param_path = os.path.join(param_dir, param_name)
        # Ensure directory exists
        os.makedirs(param_dir, exist_ok=True)
        with open(param_path, 'w') as fp:
            json.dump(user_params, fp)
    
    def update_user_chat(self, user_id, chat_id):
        '''Update user's chat_ids list to include the given chat_id if not already present'''
        user_params = self.load_user_params(user_id)
        if 'chat_ids' not in user_params:
            user_params['chat_ids'] = []
        if chat_id not in user_params['chat_ids']:
            user_params['chat_ids'].append(chat_id)
            self.save_user_params(user_id, user_params)
    
    def get_user_group_chats(self, user_id):
        '''
        Get list of group chat IDs that the user belongs to.
        Returns list of chat_ids (all are assumed to be group/supergroup chats).
        '''
        user_params = self.load_user_params(user_id)
        return user_params.get('chat_ids', [])