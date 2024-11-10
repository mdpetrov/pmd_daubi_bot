# import json
# import os

class LogOperations(object):
    def __init__(self, config):
        self.config = config
    def write_log(self, chat_id, text):
        path = self.config.path
        with open(os.path.join(path['log_dir'], f'{chat_id}.log'), mode='a') as log_con:
            log_con.write(f'{datetime.datetime.now()}: {text}\n')