"""Optional TF-IDF replies, restricted to the chat configured by the operator."""

import logging
import os
import time


MIN_REPLY_SCORE = 0.75


def classify_message(message, bot_id):
    """Return (exclude free speech, direct reply to this bot)."""
    sender = getattr(message, 'from_user', None)
    if getattr(sender, 'id', None) == bot_id:
        return True, False
    parent = getattr(message, 'reply_to_message', None)
    parent_sender = getattr(parent, 'from_user', None)
    if getattr(parent, 'poll', None) is not None and getattr(parent_sender, 'is_bot', False):
        return True, False
    return False, getattr(parent_sender, 'id', None) == bot_id


class ReplyRetrieval:
    def __init__(self):
        self.model = None
        self.last_search = {}
        self.chat_id = os.environ.get("TFIDF_CHAT_ID", "").strip()
        if not self.chat_id:
            logging.info("TF-IDF disabled: set TFIDF_CHAT_ID to the training chat ID")
            return
        try:
            import joblib
            from nlp_model.train_tfidf import DEFAULT_MODEL, search

            self.model = joblib.load(DEFAULT_MODEL)
            self.search = search
            logging.info("TF-IDF reply model loaded")
        except Exception:
            logging.exception("Cannot load TF-IDF model; using existing replies")

    def candidates(self, text, chat_id):
        if self.model is None or str(chat_id) != self.chat_id:
            return [], "disabled"
        key = str(chat_id)
        now = time.monotonic()
        if now - self.last_search.get(key, float('-inf')) < 5:
            return [], "cooldown"
        try:
            matches = self.search(
                self.model, text, top_k=len(self.model['replies']), threshold=MIN_REPLY_SCORE
            )
            return matches, "no_match" if not matches else "matched"
        except Exception:
            logging.exception("TF-IDF search failed; using existing replies")
            return [], "search_error"
        finally:
            self.last_search[key] = time.monotonic()
