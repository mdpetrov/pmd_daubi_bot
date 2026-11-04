from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import joblib
import numpy as np

from nlp_model.train_tfidf import search, train_model
from nlp_model.update_tfidf import lock_model, main


class UpdateTfidfTests(unittest.TestCase):
    def setUp(self):
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.archive = directory / '-123.jsonl'
        self.model_path = directory / 'tfidf.joblib'
        self.original = train_model({
            'schema_version': 1,
            'texts': ['Кто ещё играет?', 'Когда ужин?'],
            'replies': ['Зовите!', 'В восемь'],
        })
        joblib.dump(self.original, self.model_path)

    def append_message(self, message_id, text, reply_to=None):
        record = {'id': message_id, 'type': 'message', 'text': text}
        if reply_to is not None:
            record['reply_to_message_id'] = reply_to
        with self.archive.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')

    def run_cli(self):
        with (
            patch('sys.argv', ['update_tfidf.py', str(self.archive), '--model', str(self.model_path)]),
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            main()

    def test_appends_new_reply_and_preserves_old_scores(self):
        original_bytes = self.model_path.read_bytes()
        original_matches = search(self.original, 'Кто еще играет?')
        self.append_message(1, 'КТО ЕЩЁ ИГРАЕТ?')
        self.append_message(2, 'зовите!', reply_to=1)
        self.run_cli()
        self.assertEqual(self.model_path.read_bytes(), original_bytes)

        # The new reply's parent was already present on the preceding run.
        self.append_message(3, 'Я присоединюсь!', reply_to=1)
        self.run_cli()
        updated = joblib.load(self.model_path)
        matches = search(updated, 'Кто еще играет?')
        self.assertEqual([match for match in matches if match['index'] < 2], original_matches)
        self.assertEqual([match['reply'] for match in matches if match['index'] >= 2],
                         ['Я присоединюсь!'])
        self.assertEqual(updated['metadata']['pairs'], 3)
        for kind in ('word', 'char'):
            original_vectorizer = self.original[f'{kind}_model']
            updated_vectorizer = updated[f'{kind}_model']
            self.assertEqual(updated_vectorizer.vocabulary_, original_vectorizer.vocabulary_)
            np.testing.assert_array_equal(updated_vectorizer.idf_, original_vectorizer.idf_)

        updated_bytes = self.model_path.read_bytes()
        self.append_message(4, 'Я ПРИСОЕДИНЮСЬ!', reply_to=1)
        self.run_cli()
        self.assertEqual(self.model_path.read_bytes(), updated_bytes)

    def test_malformed_archive_leaves_model_untouched(self):
        original_bytes = self.model_path.read_bytes()
        self.append_message(1, 'Когда ужин?')
        self.append_message(2, 'Скоро', reply_to=1)
        with self.archive.open('a', encoding='utf-8') as stream:
            stream.write('{')
        with self.assertRaises(SystemExit) as error:
            self.run_cli()
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.model_path.read_bytes(), original_bytes)

    def test_failed_replacement_preserves_model_and_allows_retry(self):
        original_bytes = self.model_path.read_bytes()
        self.append_message(1, 'Когда ужин?')
        self.append_message(2, 'Скоро', reply_to=1)
        with patch.object(Path, 'replace', side_effect=PermissionError('test replacement failure')):
            with self.assertRaises(SystemExit) as error:
                self.run_cli()
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.model_path.read_bytes(), original_bytes)
        self.assertEqual(list(self.model_path.parent.glob('*.joblib')), [self.model_path])
        self.run_cli()
        self.assertIn('Скоро', joblib.load(self.model_path)['replies'])

    def test_busy_model_rejects_a_second_update(self):
        original_bytes = self.model_path.read_bytes()
        self.append_message(1, 'Когда ужин?')
        self.append_message(2, 'Скоро', reply_to=1)
        with lock_model(self.model_path):
            with self.assertRaises(SystemExit) as error:
                self.run_cli()
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(self.model_path.read_bytes(), original_bytes)
        self.run_cli()
        self.assertIn('Скоро', joblib.load(self.model_path)['replies'])

    def test_bound_model_rejects_a_different_chat_archive(self):
        self.append_message(1, 'Когда ужин?')
        self.append_message(2, 'Скоро', reply_to=1)
        self.run_cli()
        model_bytes = self.model_path.read_bytes()

        self.archive = self.archive.with_name('-456.jsonl')
        self.append_message(1, 'Когда ужин?')
        self.append_message(2, 'Завтра', reply_to=1)
        with self.assertRaises(SystemExit) as error:
            self.run_cli()
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.model_path.read_bytes(), model_bytes)
