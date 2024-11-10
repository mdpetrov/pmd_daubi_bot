import pandas as pd
from pmd_daubi_bot.bot_operation import BotOperations


class PhraseOperations(object):
    def __init__(self, config, bot):
        self.config = config
        self.BO = BotOperations(bot)
    def random_phrase(self, chat_id):
        path = self.config.path
        BO = self.BO
        BO.write_log(chat_id, ': Load phrases')
        with open(path['text_phrases'], mode='rt', encoding='utf-8') as con:
            phrases = pd.read_csv(con, sep=';')
        phrase = phrases['phrase'].sample(n=1, weights=phrases['weight']).tolist()[0]
        BO.write_log(chat_id, f'{phrase}')
        return phrase
    
    def random_readycheck_phrase(self, chat_id):
        path = self.config.path
        BO = self.BO
        with open(path['readycheck_phrases'], mode='rt', encoding='utf-8') as con:
            BO.write_log(chat_id, ': Load phrases')
            phrases = pd.read_csv(con, sep=';')
        phrases = phrases.query(f'chat_id == {chat_id}')
        phrase = phrases['phrase'].sample(n=1, weights=phrases['weight']).tolist()[0]
        BO.write_log(chat_id, f'{phrase}')
        return phrase

    