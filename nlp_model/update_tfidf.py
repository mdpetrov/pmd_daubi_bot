"""Append new reply pairs from one bot archive to an existing TF-IDF model."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import joblib
from scipy.sparse import vstack

if os.name == 'nt':
    import msvcrt
else:
    import fcntl

if __package__:
    from .prepare_training_data import load_training_source, normalize_for_search, prepare_training_data
    from .train_tfidf import DEFAULT_MODEL
else:
    from prepare_training_data import load_training_source, normalize_for_search, prepare_training_data
    from train_tfidf import DEFAULT_MODEL


@contextmanager
def lock_model(model_path):
    lock_path = model_path.with_name(model_path.name + '.lock')
    with lock_path.open('a+b') as stream:
        try:
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError(f'Could not acquire update lock for {model_path}: {error}') from error
        yield


def update_model(archive_path, model_path, max_chars=1000):
    """Update a trusted model artifact and return the number of pairs added."""
    archive_path = archive_path.resolve()
    model_path = model_path.resolve()
    if archive_path.suffix.lower() != '.jsonl' or archive_path == model_path:
        raise ValueError('Specify a chat .jsonl archive separate from the model')

    with lock_model(model_path):
        model = joblib.load(model_path)
        if (
            not isinstance(model, dict)
            or model.get('schema_version') != 1
            or model.get('normalization') != 'nfkc_whitespace_casefold_yo_v1'
        ):
            raise ValueError('Expected a compatible version 1 TF-IDF model')
        metadata = model['metadata']
        if 'chat_id' in metadata and str(metadata['chat_id']) != archive_path.stem:
            raise ValueError('Chat archive does not match the model chat ID')

        dataset = prepare_training_data(load_training_source(archive_path), max_chars)
        seen = {
            (normalize_for_search(text), normalize_for_search(reply))
            for text, reply in zip(model['texts'], model['replies'])
        }
        texts, replies = [], []
        for text, reply in zip(dataset['texts'], dataset['replies']):
            if (text, normalize_for_search(reply)) not in seen:
                texts.append(text)
                replies.append(reply)
        if not texts:
            return 0

        for kind in ('word', 'char'):
            index_key = f'{kind}_index'
            new_rows = model[f'{kind}_model'].transform(texts)
            model[index_key] = vstack((model[index_key], new_rows), format='csr')
        model['texts'].extend(texts)
        model['replies'].extend(replies)
        metadata.update(
            chat_id=archive_path.stem,
            pairs=len(model['texts']),
            sparse_index_bytes=sum(
                matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes
                for matrix in (model['word_index'], model['char_index'])
            ),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        with NamedTemporaryFile(dir=model_path.parent, suffix='.joblib', delete=False) as stream:
            temp_path = Path(stream.name)
        try:
            joblib.dump(model, temp_path, compress=3)
            temp_path.replace(model_path)
        finally:
            temp_path.unlink(missing_ok=True)
        return len(texts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--model', type=Path, default=DEFAULT_MODEL)
    parser.add_argument('--max-chars', type=int, default=1000)
    args = parser.parse_args()
    try:
        count = update_model(args.archive, args.model, args.max_chars)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f'Appended {count} new reply pairs')


if __name__ == '__main__':
    main()
