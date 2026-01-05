import json
import os

class ParamsOperations(object):
    def __init__(self, config):
        self.config = config
        self.def_params = {}
    def load_params(self):
        pass
    def save_params(self):
        pass
    def check_params(self):
        pass
class UserParamsOperations(ParamsOperations):
    def __init__(self, config):
        super().__init__(config)
        self.def_params = {'last_time_message_sent':0,
                          'last_time_message_received': 0,
                          'last_ready_check':0}
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

    def _save_params(self, entity_id, params, entity_type='chat'):
        '''Internal unified function to save params for any entity (chat or user)'''
        if not isinstance(params, dict):
            error_text = f'''Params object has type {type(params)} instead of {type(dict)}
    Debug info:
    \t{entity_type.capitalize()} id: {entity_id}'''
            raise TypeError(error_text)
        param_dir = self.config.path['data_dir']
        param_name = f"{entity_id}.param"
        param_path = os.path.join(param_dir, param_name)
        # Ensure directory exists
        os.makedirs(param_dir, exist_ok=True)
        with open(param_path, 'w') as fp:
            json.dump(params, fp)
    
    def save_params(self, chat_id, params):
        '''Save json with local parameters for the chat'''
        self._save_params(chat_id, params, entity_type='chat')
    
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
        self._save_params(user_id, user_params, entity_type='user')
    
    def update_user_chat(self, user_id, chat):
        '''Update user's chats dictionary to include the given chat. Extracts chat_id and chat name from the chat object.'''
        user_params = self.load_user_params(user_id)
        if 'chats' not in user_params:
            user_params['chats'] = {}
        
        chat_id = chat.id
        # Extract chat name from chat object (title for groups, first_name for private chats)
        chat_name = getattr(chat, 'title', None) or str(chat_id)
        
        # Store chat_id and chat_name in the dictionary
        user_params['chats'][chat_id] = chat_name
        
        self.save_user_params(user_id, user_params)
    
    def get_user_group_chats(self, user_id):
        '''
        Get list of group chat IDs that the user belongs to.
        Returns list of chat_ids (all are assumed to be group/supergroup chats).
        '''
        user_params = self.load_user_params(user_id)
        chats = user_params.get('chats', {})
        return chats if chats else None