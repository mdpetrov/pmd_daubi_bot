import json
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from pmd_daubi_bot.ready_poll_helpers import next_poll_unpin_time, prune_ready_poll_pins


def timestamp(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()


class ReadyPollPinTests(unittest.TestCase):
    def test_next_7am_utc(self):
        for created, expected in [
            ('2026-10-22T06:59:59', '2026-10-22T07:00:00'),
            ('2026-10-22T07:00:00', '2026-10-23T07:00:00'),
            ('2026-10-22T20:00:00', '2026-10-23T07:00:00'),
            ('2026-12-31T23:00:00', '2027-01-01T07:00:00'),
        ]:
            with self.subTest(created=created):
                self.assertEqual(next_poll_unpin_time(timestamp(created)), timestamp(expected))

    def test_cleanup_at_threshold_after_reload_preserves_future_pins(self):
        params = json.loads(json.dumps({'ready_poll_pins': [
            {'message_id': 10, 'unpin_at': 100},
            {'message_id': 20, 'unpin_at': 200},
        ]}))
        bot = Mock()
        prune_ready_poll_pins(bot, Mock(), 1, params, 100)
        bot.unpin_chat_message.assert_called_once_with(chat_id=1, message_id=10)
        self.assertEqual(params['ready_poll_pins'], [{'message_id': 20, 'unpin_at': 200}])

    def test_failure_is_retried_without_blocking_other_removals(self):
        params = {'ready_poll_pins': [
            {'message_id': 10, 'unpin_at': 100},
            {'message_id': 20, 'unpin_at': 100},
        ]}
        bot, log = Mock(), Mock()
        bot.unpin_chat_message.side_effect = [RuntimeError('permission denied'), None]
        prune_ready_poll_pins(bot, log, 1, params, 101)
        self.assertEqual(params['ready_poll_pins'], [{'message_id': 10, 'unpin_at': 100}])
        log.write_log.assert_called_once()
        bot.unpin_chat_message.side_effect = None
        prune_ready_poll_pins(bot, log, 1, params, 102)
        self.assertEqual(params['ready_poll_pins'], [])

    def test_old_chat_without_tracking(self):
        bot = Mock()
        params = {}
        prune_ready_poll_pins(bot, Mock(), 1, params, 100)
        bot.unpin_chat_message.assert_not_called()
        self.assertEqual(params['ready_poll_pins'], [])


if __name__ == '__main__':
    unittest.main()
