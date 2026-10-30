import unittest
from unittest.mock import Mock, patch

from pmd_daubi_bot.phrase_operation import PhraseOperations


class RegularMessageRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.phrases = PhraseOperations.__new__(PhraseOperations)
        self.phrases.reply_retrieval = Mock()
        self.phrases.random_phrase = Mock(return_value="Fallback")

    @patch("pmd_daubi_bot.phrase_operation.random.random", return_value=0.01)
    def test_regular_message_uses_matched_answer(self, _random):
        self.phrases.reply_retrieval.reply.return_value = "Historical answer"
        result = self.phrases.analyze_message_and_decide_response("Question", -123, 0)
        self.assertEqual(result, (True, "tfidf_message", "Historical answer"))
        self.phrases.reply_retrieval.reply.assert_called_once_with("Question", -123)
        self.phrases.random_phrase.assert_not_called()

    @patch("pmd_daubi_bot.phrase_operation.random.random", return_value=0.01)
    def test_no_match_uses_existing_random_phrase(self, _random):
        self.phrases.reply_retrieval.reply.return_value = None
        result = self.phrases.analyze_message_and_decide_response("Question", -123, 0)
        self.assertEqual(result, (True, "random_message", "Fallback"))

    @patch("pmd_daubi_bot.phrase_operation.random.random", return_value=0.9)
    def test_unselected_messages_do_not_search(self, _random):
        result = self.phrases.analyze_message_and_decide_response("Question", -123, 0)
        self.assertFalse(result[0])
        self.phrases.reply_retrieval.reply.assert_not_called()
        self.phrases.random_phrase.assert_not_called()


if __name__ == "__main__":
    unittest.main()
