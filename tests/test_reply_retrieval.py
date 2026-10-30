import os
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from pmd_daubi_bot.reply_retrieval import ReplyRetrieval, classify_message


class ReplyRetrievalTests(unittest.TestCase):
    def retrieval(self):
        with patch.dict(os.environ, {}, clear=True):
            instance = ReplyRetrieval()
        instance.chat_id = "-123"
        instance.model = {"replies": ["Answer"]}
        instance.search = Mock(return_value=[{"reply": "Answer", "score": .8}])
        return instance

    def test_group_restriction_and_cooldown(self):
        instance = self.retrieval()
        with patch("pmd_daubi_bot.reply_retrieval.time.monotonic", return_value=10):
            self.assertEqual(instance.candidates("Q", -456)[1], "disabled")
            instance.search.assert_not_called()
            self.assertEqual(instance.candidates("Q", -123)[1], "matched")
            self.assertEqual(instance.candidates("Q", -123)[1], "cooldown")
            self.assertEqual(instance.search.call_count, 1)
        with patch("pmd_daubi_bot.reply_retrieval.time.monotonic", return_value=15):
            self.assertEqual(instance.candidates("Q", -123)[1], "matched")

    def test_empty_search_and_failure_also_start_cooldown(self):
        for fail in (False, True):
            instance = self.retrieval()
            instance.search.return_value = []
            if fail:
                instance.search.side_effect = ValueError("Broken index")
            with patch("pmd_daubi_bot.reply_retrieval.time.monotonic", return_value=10):
                if fail:
                    with self.assertLogs(level="ERROR"):
                        self.assertEqual(instance.candidates("Q", -123)[1], "search_error")
                else:
                    self.assertEqual(instance.candidates("Q", -123)[1], "no_match")
                self.assertEqual(instance.candidates("Q", -123)[1], "cooldown")

    def test_message_exclusions(self):
        own = NS(id=1, is_bot=True)
        other_bot = NS(id=2, is_bot=True)
        user = NS(id=3, is_bot=False)
        self.assertEqual(classify_message(NS(from_user=own), 1), (True, False))
        for sender in (own, other_bot):
            parent = NS(from_user=sender, poll=object())
            self.assertEqual(classify_message(NS(from_user=user, reply_to_message=parent), 1), (True, False))
        parent = NS(from_user=own, poll=None)
        self.assertEqual(classify_message(NS(from_user=user, reply_to_message=parent), 1), (False, True))
        parent = NS(from_user=user, poll=None)
        self.assertEqual(classify_message(NS(from_user=user, reply_to_message=parent), 1), (False, False))
