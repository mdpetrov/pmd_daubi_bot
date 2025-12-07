import pandas as pd
import json
import random
import time
from os.path import join, dirname, isfile
from os import makedirs
from pmd_daubi_bot.log_operation import LogOperations


class PhraseOperations(object):
    def __init__(self, config):
        self.config = config
        self.LO = LogOperations(config)

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
            
    def load_phrases(self, chat_id=None):
        """
        Load phrases for a chat. If chat_id is provided and chat-specific file exists, load it.
        Otherwise, load default phrases (for new chats). Default file is read-only (cannot be saved to).
        """
        path = self.config.path
        # If chat_id is provided, try to load chat-specific file
        if chat_id is not None:
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
        # Ensure directory exists before trying to read
        default_dir = dirname(path['text_phrases'])
        makedirs(default_dir, exist_ok=True)
        
        # If default file doesn't exist, create it with empty list
        if not isfile(path['text_phrases']):
            with open(path['text_phrases'], mode='wt', encoding='utf-8') as con:
                json.dump([], con, indent=4, ensure_ascii=False)
            return []
        
        with open(path['text_phrases'], mode='rt', encoding='utf-8') as con:
            phrases_list = json.load(con)
        return phrases_list
    
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
    
    def analyze_message_and_decide_response(self, message_text, chat_id, last_message_time):
        """
        Analyze message content and decide whether to respond and how
        For regular messages (not replies), only respond with random phrase from text_phrases.json with 5% chance
        Returns: (should_respond, response_reason, response_phrase)
        """
        # For regular messages, only respond with 5% chance using random phrase from text_phrases.json
        # if time.time() - last_message_time >= 60 * 60 * 5: # If 5 hours passed, respond
            # should_respond = True
        # elif random.random() <= 0.05: # 5% chance
            # should_respond = True  
        # else:
        should_respond = False
        response_reason = "random_message"
        response_phrase = ""
        
        if should_respond:
            response_phrase = self.random_phrase(chat_id)
        
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
    
    def analyze_reply_to_bot(self, reply_text, chat_id=None):
        """
        Analyze reply to bot message and return appropriate response
        Returns: response_phrase or None if no response should be sent
        """
        # First check if we should respond at all (95% chance to respond to replies)
        if random.random() > 0.95:  # 5% chance to ignore
            return None
            
        keywords = self.load_response_keywords()
        reply_text_lower = reply_text.lower()
        
        # Check for all response categories in order of priority with probability checks
        # Check for gaming-related keywords
        if any(word in reply_text_lower for word in keywords['gaming_keywords']['words']):
            if random.random() <= keywords['gaming_keywords']['probability']:
                return self.random_phrase(chat_id)  # Use gaming phrases from chat-specific or default phrase database
            return None
        
        # Check for greeting keywords
        elif any(word in reply_text_lower for word in keywords['greeting_keywords']['words']):
            if random.random() <= keywords['greeting_keywords']['probability']:
                phrases = keywords['response_phrases'].get('greeting', [])
                return random.choice(phrases) if phrases else "здорова 👋"
            return None
        
        # Check for question keywords
        elif any(word in reply_text_lower for word in keywords['question_keywords']['words']):
            if random.random() <= keywords['question_keywords']['probability']:
                phrases = keywords['response_phrases'].get('question', [])
                return random.choice(phrases) if phrases else "А хуй его знает, чел.. 🤔"
            return None
        
        # Check for agreement keywords
        elif any(word in reply_text_lower for word in keywords['agreement_keywords']['words']):
            if random.random() <= keywords['agreement_keywords']['probability']:
                phrases = keywords['response_phrases'].get('agreement', [])
                return random.choice(phrases) if phrases else "найс найс найс 👍"
            return None
        
        # Check for disagreement keywords
        elif any(word in reply_text_lower for word in keywords['disagreement_keywords']['words']):
            if random.random() <= keywords['disagreement_keywords']['probability']:
                phrases = keywords['response_phrases'].get('disagreement', [])
                return random.choice(phrases) if phrases else "да мне поебать"
            return None
        
        # Check for negative sentiment
        elif any(word in reply_text_lower for word in keywords['negative_keywords']['words']):
            if random.random() <= keywords['negative_keywords']['probability']:
                phrases = keywords['response_phrases'].get('negative', [])
                return random.choice(phrases) if phrases else "Без негатива же..."
            return None
        
        # Check for positive sentiment
        elif any(word in reply_text_lower for word in keywords['positive_keywords']['words']):
            if random.random() <= keywords['positive_keywords']['probability']:
                phrases = keywords['response_phrases'].get('positive', [])
                return random.choice(phrases) if phrases else "Охуенно! 😊"
            return None
        
        else:
            # For neutral replies, use a random phrase from text_phrases.json
            # Since we already have 95% chance to respond, we'll use the phrase database
            return self.random_phrase(chat_id)  # Use weighted phrase selection for neutral replies (chat-specific or default phrases)