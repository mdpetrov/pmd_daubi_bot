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
            rng.assert_called_once_with()
        return result

    def test_shared_draw_boundaries(self):
        fallback = (True, 'random_no_match', 'Fallback')
        match = (True, 'tfidf_high', 'Matched')
        cases = [(None, .05, fallback), (.5, .05, fallback), (.749, .05, fallback),
                 (.75, .5, match), (1, .5, match)]
        for is_reply in (False, True):
            for score, cutoff, expected in cases:
                with self.subTest(score=score, is_reply=is_reply):
                    self.assertEqual(self.decide(score, cutoff, is_reply), expected)
                    self.assertFalse(self.decide(score, cutoff + .001, is_reply)[0])

    def test_early_gate_never_searches(self):
        self.assertFalse(self.decide(.9, .9)[0])
        self.phrases.reply_retrieval.candidates.assert_not_called()

    def test_cooldown_uses_random_fallback(self):
        self.assertEqual(self.decide(None, .01, status="cooldown"), (True, "random_cooldown", "Fallback"))
        self.assertFalse(self.decide(None, .2, status="cooldown")[0])
        self.assertEqual(self.decide(None, .05, is_reply=True, status="cooldown"),
                         (True, "random_cooldown", "Fallback"))

    def test_highest_band_only_and_deduplication(self):
        self.phrases.reply_retrieval.candidates.return_value = ([
            {"score": .6, "reply": "Medium"}, {"score": .8, "reply": "High"},
            {"score": .9, "reply": "High"}, {"score": .95, "reply": "Other"}], "matched")
        with (
            patch("pmd_daubi_bot.phrase_operation.random.random", return_value=.5),
            patch("pmd_daubi_bot.phrase_operation.random.choice", return_value="High") as choice,
        ):
            self.assertEqual(self.phrases.decide_free_speech("Q", -123, True)[2], "High")
            choice.assert_called_once_with(["High", "Other"])
