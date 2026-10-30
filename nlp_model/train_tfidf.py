"""Fit and save a CPU-only word/character TF-IDF reply retrieval model."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer

if __package__:
    from .prepare_training_data import DEFAULT_OUTPUT, normalize_for_search
else:
    from prepare_training_data import DEFAULT_OUTPUT, normalize_for_search


DEFAULT_MODEL = Path(__file__).resolve().parent.parent / ".secret" / "nlp_model" / "tfidf.joblib"


def train_model(dataset, word_features=30_000, char_features=50_000):
    """Return a portable bundle of vectorizers, sparse indices and aligned replies."""
    if not isinstance(dataset, dict) or dataset.get("schema_version") != 1:
        raise ValueError("Expected a version 1 dataset from prepare_training_data.py")
    texts, replies = dataset.get("texts"), dataset.get("replies")
    if not isinstance(texts, list) or not isinstance(replies, list):
        raise ValueError("Dataset must contain texts and replies lists")
    if not texts or len(texts) != len(replies):
        raise ValueError("Dataset must contain nonempty, equally sized texts and replies")
    if any(not isinstance(s, str) or not s.strip() for s in texts + replies):
        raise ValueError("All texts and replies must be nonempty strings")
    if word_features < 1 or char_features < 1:
        raise ValueError("Feature limits must be positive")
    texts = [normalize_for_search(text) for text in texts]
    word_model = TfidfVectorizer(
        ngram_range=(1, 2), token_pattern=r"(?u)\b\w+\b",
        max_features=word_features, sublinear_tf=True, dtype=np.float32,
    )
    char_model = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5),
        max_features=char_features, sublinear_tf=True, dtype=np.float32,
    )
    word_index = word_model.fit_transform(texts).tocsr()
    char_index = char_model.fit_transform(texts).tocsr()
    return {
        "schema_version": 1,
        "normalization": "nfkc_whitespace_casefold_yo_v1",
        "word_model": word_model, "char_model": char_model,
        "word_index": word_index, "char_index": char_index,
        "word_weight": 0.6,
        "texts": texts, "replies": replies,
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sklearn_version": sklearn.__version__,
            "numpy_version": np.__version__,
            "pairs": len(texts),
            "word_features": word_index.shape[1],
            "char_features": char_index.shape[1],
            "sparse_index_bytes": sum(
                matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes
                for matrix in (word_index, char_index)
            ),
        },
    }


def search(model, text, top_k=5, threshold=0.25):
    """Return matching prompts and their replies; scores are not probabilities.

    The initial threshold is heuristic and needs tuning on real conversations.
    Only the score vector is dense; historical feature matrices stay sparse.
    """
    if top_k < 1 or not 0 <= threshold <= 1:
        raise ValueError("top_k must be positive and threshold must be between 0 and 1")
    text = normalize_for_search(text)
    if not text:
        return []
    word_scores = (model["word_index"] @ model["word_model"].transform([text]).T).toarray().ravel()
    char_scores = (model["char_index"] @ model["char_model"].transform([text]).T).toarray().ravel()
    weight = model["word_weight"]
    scores = weight * word_scores + (1 - weight) * char_scores
    candidates = np.flatnonzero((scores > 0) & (scores >= threshold))
    best = candidates[np.argsort(-scores[candidates], kind="stable")[:top_k]]
    return [
        {"index": int(i), "score": float(scores[i]),
         "text": model["texts"][i], "reply": model["replies"][i]}
        for i in best
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--word-features", type=int, default=30_000)
    parser.add_argument("--char-features", type=int, default=50_000)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Output must differ from the prepared dataset")
    start = time.perf_counter()
    try:
        with args.input.open(encoding="utf-8-sig") as stream:
            dataset = json.load(stream)
        model = train_model(dataset, args.word_features, args.char_features)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, args.output, compress=3)
    print(json.dumps({**model["metadata"],
        "training_seconds": round(time.perf_counter() - start, 3),
        "artifact_bytes": args.output.stat().st_size,
    }, indent=2))
    print(f"Saved model to {args.output}")


if __name__ == "__main__":
    main()
