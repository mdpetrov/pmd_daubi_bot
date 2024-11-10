import pandas as pd
from pmd_daubi_bot.log_operation import LogOperations


class PhraseOperations(object):
    def __init__(self, config):
        self.config = config
        self.LO = LogOperations(config)
        
    def random_phrase(self, chat_id):
        path = self.config.path
        LO = self.LO
        LO.write_log(chat_id, ': Load phrases')
        with open(path['text_phrases'], mode='rt', encoding='utf-8') as con:
            phrases = pd.read_csv(con, sep=';')
        phrase = phrases['phrase'].sample(n=1, weights=phrases['weight']).tolist()[0]
        LO.write_log(chat_id, f'{phrase}')
        return phrase
    
    def random_readycheck_phrase(self, chat_id):
        path = self.config.path
        LO = self.LO
        param_value = self.config.param_value
        with open(path['readycheck_phrases'], mode='rt', encoding='utf-8') as con:
            LO.write_log(chat_id, ': Load phrases')
            phrases = pd.read_csv(con, sep=';')
        phrases = phrases.query(f'chat_id == {chat_id}')
        if len(phrases) == 0: #no phrase for this chat, putting the default one
            LO.write_log(chat_id, 'Phrase list for the chat not found; putting the default one')
            return param_value['readycheck_default_phrase']
        phrase = phrases['phrase'].sample(n=1, weights=phrases['weight']).tolist()[0]
        LO.write_log(chat_id, f'{phrase}')
        return phrase
    def add_phrase(self, phrase):
        path = self.config.path
        LO = self.LO
        LO.write_log(chat_id, ': Load phrases')
        with open(path['text_phrases'], mode='rt', encoding='utf-8') as con:
            phrases = pd.read_csv(con, sep=';')
        if phrase in phrases['phrase']:
            return 'Такая фраза уже есть'
        else:
            phrases.loc[len(phrases)] = (phrase, 0.5)
            phrases.to_csv(path['text_phrases'], encoding='utf-8', index=False, sep=';')
            return 'Успешно добавлено!'