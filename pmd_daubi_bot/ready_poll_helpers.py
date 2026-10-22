"""Persisted, lazy cleanup of readiness poll pins."""

from datetime import datetime, timedelta, timezone


def next_poll_unpin_time(created_at):
    """Return the first 07:00 UTC strictly after creation, as a timestamp."""
    created = datetime.fromtimestamp(created_at, timezone.utc)
    threshold = created.replace(hour=7, minute=0, second=0, microsecond=0)
    if threshold <= created:
        threshold += timedelta(days=1)
    return threshold.timestamp()


def prune_ready_poll_pins(bot, log, chat_id, params, now):
    """Unpin expired tracked polls; retain failures to retry on later activity."""
    pending = []
    for poll in params.get('ready_poll_pins', []):
        if poll['unpin_at'] > now:
            pending.append(poll)
            continue
        try:
            bot.unpin_chat_message(chat_id=chat_id, message_id=poll['message_id'])
        except Exception as error:
            log.write_log(chat_id, f'Failed to unpin ready poll {poll["message_id"]}: {error}')
            pending.append(poll)
    params['ready_poll_pins'] = pending
