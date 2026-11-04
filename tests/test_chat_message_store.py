import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from nlp_model.prepare_training_data import load_training_source, prepare_training_data
from pmd_daubi_bot.chat_message_store import ChatMessageStore


def make_message(chat_id, message_id, text, *, reply_to=None, chat_type='group', is_bot=False):
    return SimpleNamespace(
        chat=SimpleNamespace(id=chat_id, type=chat_type),
        message_id=message_id,
        date=1234567890,
        text=text,
        from_user=SimpleNamespace(is_bot=is_bot),
        reply_to_message=reply_to,
    )


class ChatMessageStoreTests(unittest.TestCase):
    def test_saved_chat_can_be_prepared_for_training(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ChatMessageStore(directory)
            prompt = make_message(-1, 1, '¿Qué tal?\nПривет!')
            store.append(prompt)
            store.append(make_message(-2, 1, 'A separate chat'))
            store.append(make_message(-1, 2, '¡Bien! 🙂', reply_to=prompt))

            archive = Path(directory) / 'chat_messages'
            self.assertEqual({file.name for file in archive.iterdir()}, {'-1.jsonl', '-2.jsonl'})
            source = load_training_source(archive / '-1.jsonl')
            other = load_training_source(archive / '-2.jsonl')
            self.assertEqual([record['id'] for record in source['messages']], [1, 2])
            self.assertEqual(source['messages'][0]['text'], prompt.text)
            self.assertEqual(other['messages'][0]['text'], 'A separate chat')
            prepared = prepare_training_data(source)
            self.assertEqual(prepared['texts'], ['¿qué tal? привет!'])
            self.assertEqual(prepared['replies'], ['¡Bien! 🙂'])

    def test_private_messages_commands_and_bot_messages_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ChatMessageStore(directory)
            store.append(make_message(-1, 1, '/ready_poll'))
            store.append(make_message(-1, 2, 'Bot response', is_bot=True))
            store.append(make_message(1, 1, 'Private text', chat_type='private'))
            self.assertEqual(list(Path(directory).iterdir()), [])
