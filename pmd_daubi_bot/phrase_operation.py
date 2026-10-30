import pandas as pd
import json
import random
import time
from os.path import join, dirname, isfile
from os import makedirs
from pmd_daubi_bot.log_operation import LogOperations
from pmd_daubi_bot.reply_retrieval import ReplyRetrieval


class PhraseOperations(object):
    def __init__(self, config):
        self.config = config
        self.LO = LogOperations(config)
        self.reply_retrieval = ReplyRetrieval()

    def random_phrase(self, chat_id):
        """
        Get a random phrase for a chat. If chat_id is None, uses default phrases (read-only).
        For group chats, uses chat-specific phrases.
        """
        path = self.config.path
        weight = self.config.weight
        LO = self.LO
        LO.write_log(chat_id if chat_id else 0, ': Load phrases')
        phrases = self.load_phrases(chat_id)
        
        # Handle empty phrase list
        if not phrases:
            LO.write_log(chat_id if chat_id else 0, 'Phrase list is empty')
            return "Нет фраз"
        
        phrases = pd.DataFrame(phrases)
            
        selected_phrase_df = phrases['phrase'].sample(n=1, weights=phrases['weight'])
        vec_to_decrease = phrases.index.isin(selected_phrase_df.index)
        vec_to_increase = ~phrases.index.isin(selected_phrase_df.index)
        
        phrases.loc[vec_to_decrease, 'weight'] = phrases.loc[vec_to_decrease, 'default_weight'] # Set default weight to selected phrase
        phrases.loc[vec_to_increase, 'weight'] = phrases.loc[vec_to_increase, 'weight'] + weight['increase'] # Increase weight to not selected phrases
        
        # Only save if chat_id is provided (group chat) - never save changes to default
        if chat_id is not None:
            self.save_phrases(chat_id, phrases.to_dict(orient='records'))
        
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
        
    def add_phrase(self, phrase, chat_id):
        """
        Add a phrase to a group chat's phrase list.
        chat_id is REQUIRED - phrases can only be added to group/supergroup chats.
        """
        if chat_id is None:
            raise ValueError("chat_id is required. Phrases can only be added to group/supergroup chats.")
        
        weight = self.config.weight
        LO = self.LO
        LO.write_log(chat_id, f'Trying to add a new phrase to chat {chat_id}')
        # Load phrases for this specific chat
        phrases = self.load_phrases(chat_id)
        
        # Check if phrase already exists (case-insensitive)
        if phrase.lower() in [p['phrase'].lower() for p in phrases]:
            return 'Такая фраза уже есть'
        else:
            # Add new phrase with proper structure for JSON format
            new_phrase = {
                'phrase': phrase,
                'weight': 1000000,  # Set the current value very high
                'default_weight': weight['base']  # Set the default value normal
            }
            phrases.append(new_phrase)
            # Save to chat-specific file (will create if doesn't exist)
            self.save_phrases(chat_id, phrases)
            return 'Легчайшее добавление'
            
    def load_phrases(self, chat_id):
        """
        Load phrases for a chat. If chat_id is provided and chat-specific file exists, load it.
        Otherwise, load default phrases (for new chats). Default file is read-only (cannot be saved to).
        """
        if chat_id is None:
            raise ValueError("chat_id is required. Phrases can only be loaded from group chat files.")
        path = self.config.path
        # Build chat-specific path using the same directory as the default text_phrases file
        default_dir = dirname(path['text_phrases'])
        # Ensure directory exists (might be first time creating it)
        makedirs(default_dir, exist_ok=True)
        chat_specific_filename = f"{chat_id}.json"
        chat_specific_path = join(default_dir, chat_specific_filename)
        if isfile(chat_specific_path):
            # Load chat-specific phrases
            with open(chat_specific_path, mode='rt', encoding='utf-8') as con:
                phrases_list = json.load(con)
            return phrases_list
       
        # Load default phrases file (fallback for new chats or when chat_id is None)
        if isfile(path['text_phrases']):
            with open(path['text_phrases'], mode='rt', encoding='utf-8') as con:
                phrases_list = json.load(con)
            self.save_phrases(chat_id, phrases_list)
            return phrases_list
        else:
            with open(path['text_phrases'], mode='wt', encoding='utf-8') as con:
                json.dump({}, con, indent=4, ensure_ascii=False)
        
    
    def save_phrases(self, chat_id, phrases):
        """
        Save phrases to chat-specific file. 
        chat_id is REQUIRED - this method only saves to group chat files, never to default.
        """
        if chat_id is None:
            raise ValueError("chat_id is required. Cannot save to default phrase list - it is protected.")
        
        path = self.config.path
        # Build chat-specific path using the same directory as the default text_phrases file
        default_dir = dirname(path['text_phrases'])
        chat_specific_filename = f"{chat_id}.json"
        chat_specific_path = join(default_dir, chat_specific_filename)
        # Ensure directory exists
        makedirs(default_dir, exist_ok=True)
        # Save phrases as JSON to chat-specific file
        with open(chat_specific_path, mode='wt', encoding='utf-8') as con:
            json.dump(phrases, con, indent=4, ensure_ascii=False)
    
    def load_response_keywords(self):
        """Load response keywords and their probabilities from JSON file"""
        path = self.config.path
        with open(path['response_keywords'], mode='rt', encoding='utf-8') as con:
            keywords = json.load(con)
        return keywords
    
    def decide_free_speech(self, message_text, chat_id, is_reply=False):
        """Use one probability draw for the early gate and score-band decision."""
        draw = None if is_reply else random.random()
        if draw is not None and draw > 0.5:
            return False, "probability_gate", None

        matches, status = self.reply_retrieval.candidates(message_text, chat_id)
        high = [match for match in matches if match['score'] >= 0.75]
        medium = [match for match in matches if 0.5 <= match['score'] < 0.75]
        band = high or medium
        if band:
            probability = 0.5 if high else 0.1
            reason = "tfidf_high" if high else "tfidf_medium"
            if is_reply or draw <= probability:
                replies = list(dict.fromkeys(match['reply'] for match in band))
                return True, reason, random.choice(replies)
            return False, reason + "_silent", None

        if is_reply or draw <= 0.05:
            return True, "random_" + status, self.random_phrase(chat_id)
        return False, "silent_" + status, None

    def analyze_message_and_decide_response(self, message_text, chat_id, last_message_time):
        return self.decide_free_speech(message_text, chat_id)

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
    
    def analyze_reply_to_bot(self, reply_text, chat_id=None):
        should_respond, _, phrase = self.decide_free_speech(reply_text, chat_id, is_reply=True)
        return phrase if should_respond else None
