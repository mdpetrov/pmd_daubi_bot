import json
from pathlib import Path
from threading import Lock


class ChatMessageStore:
    def __init__(self, data_dir):
        self.directory = Path(data_dir) / 'chat_messages'
        self._lock = Lock()

    def append(self, message):
        """Record human conversation text in a per-chat training source."""
        if message.chat.type not in {'group', 'supergroup'}:
            return
        if not message.text or message.text.lstrip().startswith('/'):
            return
        if getattr(message.from_user, 'is_bot', False):
            return

        record = {
            'id': message.message_id,
            'type': 'message',
            'date_unixtime': message.date,
            'text': message.text,
        }
        parent = getattr(message, 'reply_to_message', None)
        if parent is not None and parent.chat.id == message.chat.id:
            record['reply_to_message_id'] = parent.message_id
        if getattr(message, 'forward_origin', None) or getattr(message, 'forward_date', None):
            record['forwarded_from'] = True

        line = json.dumps(record, ensure_ascii=False) + '\n'
        archive_path = self.directory / f'{message.chat.id}.jsonl'
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            with archive_path.open('a', encoding='utf-8') as stream:
                stream.write(line)
