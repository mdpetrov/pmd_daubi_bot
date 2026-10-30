import os
import unittest
from unittest.mock import Mock, patch

from pmd_daubi_bot.reply_retrieval import ReplyRetrieval


class ReplyRetrievalTests(unittest.TestCase):
    def retrieval(self):
        with patch.dict(os.environ, {}, clear=True):
            instance = ReplyRetrieval()
        instance.chat_id = "-123"
        instance.model = {}
        instance.threshold = 0.25
        instance.search = Mock(return_value=[{"reply": "Matched reply"}])
        return instance

    def test_returns_match_only_in_training_chat(self):
        instance = self.retrieval()
        self.assertIsNone(instance.reply("Hello", -456))
        instance.search.assert_not_called()
        self.assertEqual(instance.reply("Hello", -123), "Matched reply")

    def test_no_match_and_failure_allow_fallback(self):
        instance = self.retrieval()
        instance.search.return_value = []
        self.assertIsNone(instance.reply("Hello", -123))
        instance.search.side_effect = ValueError("Broken index")
        with self.assertLogs(level="ERROR"):
            self.assertIsNone(instance.reply("Hello", -123))

    def test_disabled_without_chat_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            instance = ReplyRetrieval()
        self.assertIsNone(instance.model)
        self.assertIsNone(instance.reply("Hello", -123))


if __name__ == "__main__":
    unittest.main()
