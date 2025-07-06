import pandas as pd
import json
from pmd_daubi_bot.log_operation import LogOperations


class PhraseOperations(object):
    def __init__(self, config):
        self.config = config
        self.LO = LogOperations(config)

    def random_phrase(self, chat_id):
        path = self.config.path
        weight = self.config.weight
        LO = self.LO
        LO.write_log(chat_id, ': Load phrases')
        phrases = self.load_phrases()
        phrases = pd.DataFrame(phrases)
            
        selected_phrase_df = phrases['phrase'].sample(n=1, weights=phrases['weight'])
        vec_to_decrease = phrases.index.isin(selected_phrase_df.index)
        vec_to_increase = ~phrases.index.isin(selected_phrase_df.index)
        
        phrases.loc[vec_to_decrease, 'weight'] = phrases.loc[vec_to_decrease, 'default_weight'] # Set default weight to selected phrase
        phrases.loc[vec_to_increase, 'weight'] = phrases.loc[vec_to_increase, 'weight'] + weight['increase'] # Increase weight to not selected phrases
        
        self.save_phrases(phrases.to_dict(orient='records'))
        
        phrase = selected_phrase_df.tolist()[0]
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
        weight = self.config.weight
        LO = self.LO
        LO.write_log(0, 'Trying to add a new phrase')
        phrases = self.load_phrases()
        phrases = pd.DataFrame(phrases)
        if phrase.lower() in [s.lower() for s in phrases['phrase'].tolist()]:
            return 'Такая фраза уже есть'
        else:
            phrases.loc[len(phrases)] = (phrase, 10000, weight['base']) # Set the current value very high but the default value normal
            self.save_phrases(phrases.to_dict(orient='records'))
            return 'Легчайшее добавление'
            
    def load_phrases(self):
        path = self.config.path
        with open(path['text_phrases'], mode='rt', encoding='utf-8') as con:
            phrase_dict = json.load(con)
        return phrase_dict
    def save_phrases(self, phrases):
        path = self.config.path
        with open(path['text_phrases'], mode='wt', encoding='utf-8') as con:
            json.dump(phrases, con)