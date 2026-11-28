import os
import datetime
import logging

class LogOperations(object):
    def __init__(self, config):
        self.config = config
    def write_log(self, chat_id, text):
        # Missing/invalid chat IDs belong in the general log, never in 0.log.
        if chat_id is None or str(chat_id).strip() in {'', '0'}:
            logging.info('%s', text)
            return
        path = self.config.path
        with open(os.path.join(path['log_dir'], f'{chat_id}.log'), mode='a') as log_con:
            log_con.write(f'{datetime.datetime.now()}: {text}\n')
