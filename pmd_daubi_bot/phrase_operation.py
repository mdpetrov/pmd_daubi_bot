import pandas as pd
from pmd_daubi_bot.bot_operation import BotOperations

BO = BotOperations(bot)

class PhraseOperations(object):
    def __init__(self, config):
        self.config = config
    def random_phrase(self, chat_id):
        path = self.config.path
        with open(path['text_phrases'], mode='rt', encoding='utf-8') as con:
            BO.write_log(chat_id, ': Load phrases')
            phrases = pd.read_csv(con, sep=';')
            phrase = phrases['phrase'].sample(n=1, weights=phrases['weight']).tolist()[0]
            BO.write_log(chat_id, f'{phrase}')
            return phrase

    