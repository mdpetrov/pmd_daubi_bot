# import json
# import os
# from time import time

class PhraseOperations(object):
    def __init__(self, config):
        self.config = config
    def random_phrase(self, chat_id):
        path = self.config.path
        with open(path['text_phrases'], mode='rt', encoding='utf-8') as con:
            write_log(chat_id, ': Load phrases')
            phrases = pd.read_csv(con, sep=';')
            phrase = phrases['phrase'].sample(n=1, weights=phrases['weight']).tolist()[0]
            write_log(chat_id, f'{phrase}')
            return phrase

    