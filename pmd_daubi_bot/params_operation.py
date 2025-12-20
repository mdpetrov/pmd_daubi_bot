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
            # Migrate old format (chat_ids + chat_names) to new format (chats dict)
            if 'chat_ids' in user_params or 'chat_names' in user_params:
                chats = {}
                # Get existing chat_ids
                chat_ids = user_params.get('chat_ids', [])
                chat_names = user_params.get('chat_names', {})
                # Merge into new format
                for cid in chat_ids:
                    # Convert chat_id to int if it's in the list
                    cid_int = int(cid) if isinstance(cid, (str, int)) else cid
                    chats[cid_int] = chat_names.get(cid_int, chat_names.get(str(cid_int), str(cid_int)))
                user_params['chats'] = chats
                # Remove old keys
                user_params.pop('chat_ids', None)
                user_params.pop('chat_names', None)
            # Ensure chats dict exists
            if 'chats' not in user_params:
                user_params['chats'] = {}
        else:
            user_params = {'chats': {}}
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
    
    def update_user_chat(self, user_id, chat_id, bot=None):
        '''Update user's chats dictionary to include the given chat_id. Stores chat name if bot is provided or if not already stored.'''
        user_params = self.load_user_params(user_id)
        if 'chats' not in user_params:
            user_params['chats'] = {}
        
        # Get and store chat name if not already stored or if bot is provided (to update existing)
        if chat_id not in user_params['chats'] or bot is not None:
            if bot is not None:
                try:
                    chat_info = bot.get_chat(chat_id)
                    chat_name = getattr(chat_info, 'title', None) or getattr(chat_info, 'first_name', None) or str(chat_id)
                    user_params['chats'][chat_id] = chat_name
                except Exception:
                    # If we can't get chat info and name not stored, use chat_id as name
                    if chat_id not in user_params['chats']:
                        user_params['chats'][chat_id] = str(chat_id)
            else:
                # If bot not provided and chat not in dict, use chat_id as name
                user_params['chats'][chat_id] = str(chat_id)
        
        self.save_user_params(user_id, user_params)
    
    def get_user_group_chats(self, user_id):
        '''
        Get list of group chat IDs that the user belongs to.
        Returns list of chat_ids (all are assumed to be group/supergroup chats).
        '''
        user_params = self.load_user_params(user_id)
        chats = user_params.get('chats', {})
        return chats if chats else None