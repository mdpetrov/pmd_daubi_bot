"""Optional TF-IDF replies, restricted to the chat configured by the operator."""

import logging
import os


class ReplyRetrieval:
    def __init__(self):
        self.model = None
        self.chat_id = os.environ.get("TFIDF_CHAT_ID", "").strip()
        if not self.chat_id:
            logging.info("TF-IDF disabled: set TFIDF_CHAT_ID to the training chat ID")
            return
        try:
            import joblib
            from nlp_model.train_tfidf import DEFAULT_MODEL, search

            self.threshold = float(os.environ.get("TFIDF_THRESHOLD", "0.25"))
            if not 0 <= self.threshold <= 1:
                raise ValueError("TFIDF_THRESHOLD must be between 0 and 1")
            self.model = joblib.load(DEFAULT_MODEL)
            self.search = search
            logging.info("TF-IDF reply model loaded")
        except Exception:
            logging.exception("Cannot load TF-IDF model; using existing replies")

    def reply(self, text, chat_id):
        if self.model is None or str(chat_id) != self.chat_id:
            return None
        try:
            matches = self.search(self.model, text, top_k=1, threshold=self.threshold)
            return matches[0]["reply"] if matches else None
        except Exception:
            logging.exception("TF-IDF search failed; using existing replies")
            return None
