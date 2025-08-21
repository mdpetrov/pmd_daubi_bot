import pandas as pd
import json
import random
import time
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
            json.dump(phrases, con, indent=4, ensure_ascii=False)
    
    def load_response_keywords(self):
        """Load response keywords and their probabilities from JSON file"""
        path = self.config.path
        with open(path['response_keywords'], mode='rt', encoding='utf-8') as con:
            keywords = json.load(con)
        return keywords
    
    def analyze_message_and_decide_response(self, message_text, chat_id, last_message_time):
        """
        Analyze message content and decide whether to respond and how
        Returns: (should_respond, response_reason, response_phrase)
        """
        keywords = self.load_response_keywords()
        message_text_lower = message_text.lower()
        should_respond = False
        response_reason = ""
        response_phrase = ""
        
        # Check for specific triggers that warrant a response
        for category, data in keywords.items():
            if category in ['random_response_probability', 'time_based_cooldown_hours', 'response_phrases']:
                continue
                
            if any(word in message_text_lower for word in data['words']):
                should_respond = random.random() <= data['probability']
                response_reason = data['response_type']
                break
        
        # If no specific keywords found, check random response probability
        if not response_reason:
            should_respond = random.random() <= keywords['random_response_probability']
            response_reason = "random"
        
        # Time-based cooldown check
        cooldown_config = keywords['time_based_cooldown_hours']
        auto_send_cd_h = random.uniform(cooldown_config['min'], cooldown_config['max'])
        if time.time() - last_message_time >= auto_send_cd_h * 3600:
            should_respond = True
            response_reason = "time_based"
        
        # Choose appropriate phrase based on context
        if should_respond:
            response_phrase = self._get_contextual_phrase(response_reason, chat_id)
        
        return should_respond, response_reason, response_phrase
    
    def _get_contextual_phrase(self, response_reason, chat_id):
        """Get appropriate phrase based on response reason"""
        keywords = self.load_response_keywords()
        
        if response_reason == "gaming_related":
            return self.random_phrase(chat_id)
        elif response_reason in ["greeting", "question", "agreement", "disagreement", "negative", "positive"]:
            # Get phrases for this response type
            phrases = keywords['response_phrases'].get(response_reason, [])
            if phrases:
                return random.choice(phrases)
            else:
                # Fallback to random phrase if no specific phrases found
                return self.random_phrase(chat_id)
        else:
            return self.random_phrase(chat_id)
    
    def analyze_reply_to_bot(self, reply_text):
        """
        Analyze reply to bot message and return appropriate response
        Returns: response_phrase
        """
        keywords = self.load_response_keywords()
        reply_text_lower = reply_text.lower()
        
        # Check for negative sentiment
        if any(word in reply_text_lower for word in keywords['negative_keywords']['words']):
            phrases = keywords['response_phrases'].get('negative', [])
            return random.choice(phrases) if phrases else "Без негатива же..."
        # Check for positive sentiment
        elif any(word in reply_text_lower for word in keywords['positive_keywords']['words']):
            phrases = keywords['response_phrases'].get('positive', [])
            return random.choice(phrases) if phrases else "Охуенно! 😊"
        # Check for questions
        elif any(word in reply_text_lower for word in keywords['question_keywords']['words']):
            phrases = keywords['response_phrases'].get('question', [])
            return random.choice(phrases) if phrases else "А хуй его знает, чел.. 🤔"
        else:
            # Use weighted phrase selection for neutral replies
            return None  # This will be handled by calling random_phrase in main.py