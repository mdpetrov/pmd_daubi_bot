import unittest
from unittest.mock import Mock, patch
from pmd_daubi_bot.phrase_operation import PhraseOperations


class FreeSpeechTests(unittest.TestCase):
    def setUp(self):
        self.phrases = PhraseOperations.__new__(PhraseOperations)
        self.phrases.reply_retrieval = Mock()
        self.phrases.random_phrase = Mock(return_value="Fallback")

    def decide(self, score, draw, is_reply=False, status="no_match"):
        matches = [] if score is None else [{"score": score, "reply": "Matched"}]
        self.phrases.reply_retrieval.candidates.return_value = matches, status
        with patch("pmd_daubi_bot.phrase_operation.random.random", return_value=draw) as rng:
            result = self.phrases.decide_free_speech("Question", -123, is_reply)
            self.assertEqual(rng.call_count, 0 if is_reply else 1)
        return result

    def test_shared_draw_boundaries(self):
        for score, cutoff in [(None, .05), (.5, .1), (.749, .1), (.75, .5), (1, .5)]:
            with self.subTest(score=score):
                self.assertTrue(self.decide(score, cutoff)[0])
                self.assertFalse(self.decide(score, cutoff + .001)[0])

    def test_early_gate_never_searches(self):
        self.assertFalse(self.decide(.9, .9)[0])
        self.phrases.reply_retrieval.candidates.assert_not_called()

    def test_direct_replies_always_answer(self):
        for score in (None, .6, .9):
            self.assertTrue(self.decide(score, .99, is_reply=True)[0])

    def test_cooldown_uses_random_fallback(self):
        self.assertEqual(self.decide(None, .01, status="cooldown"), (True, "random_cooldown", "Fallback"))
        self.assertFalse(self.decide(None, .2, status="cooldown")[0])
        self.assertTrue(self.decide(None, .9, is_reply=True, status="cooldown")[0])

    def test_highest_band_only_and_deduplication(self):
        self.phrases.reply_retrieval.candidates.return_value = ([
            {"score": .6, "reply": "Medium"}, {"score": .8, "reply": "High"},
            {"score": .9, "reply": "High"}, {"score": .95, "reply": "Other"}], "matched")
        with patch("pmd_daubi_bot.phrase_operation.random.choice", return_value="High") as choice:
            self.assertEqual(self.phrases.decide_free_speech("Q", -123, True)[2], "High")
            choice.assert_called_once_with(["High", "Other"])
