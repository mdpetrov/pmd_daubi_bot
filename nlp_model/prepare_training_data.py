"""Extract text-only message/reply pairs from a Telegram JSON export.

Usage: python nlp_model/prepare_training_data.py [export.json] [-o prepared.json]
Without an input path, uses the sole JSON in .secret/training_data.
The default output also stays in that ignored, private directory.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import unicodedata


TRAINING_DIR = Path(__file__).resolve().parent.parent / ".secret" / "nlp_model" / "training_data"
DEFAULT_OUTPUT = TRAINING_DIR.parent() / "prepared_tfidf.json"
MEDIA_FIELDS = (
    "photo", "file", "media_type", "poll", "contact_information",
    "contact_vcard", "location_information", "rich_message",
)


def flatten_text(value):
    """Telegram represents formatted text as strings mixed with entity objects."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(
            part if isinstance(part, str) else part.get("text", "")
            for part in value
            if isinstance(part, (str, dict))
        )
    return ""


def clean_text(value):
    text = unicodedata.normalize("NFKC", flatten_text(value))
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_search(text):
    """Apply this same normalization to incoming messages before searching."""
    return clean_text(text).casefold().replace("ё", "е")


def usable_text(message, max_chars):
    if message.get("type") != "message":
        return ""
    if any(field in message for field in MEDIA_FIELDS):
        return ""
    if "forwarded_from" in message or "forwarded_from_id" in message:
        return ""
    text = clean_text(message.get("text"))
    if not text or len(text) > max_chars or text.startswith("/"):
        return ""
    # Emoji-only/punctuation-only messages do not provide useful lexical matches.
    if not any(character.isalnum() for character in text):
        return ""
    return text


def prepare_training_data(export, max_chars=1000):
    """Return a JSON-serializable TF-IDF dataset, using explicit replies only.

    texts[i] is a normalized historical prompt; replies[i] is its actual answer.
    Distinct answers to the same prompt are preserved. Exact duplicate pairs
    are removed. No speaker names or account IDs are included in the output.
    """
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    if not isinstance(export, dict) or not isinstance(export.get("messages"), list):
        raise ValueError("Expected a Telegram chat export with a 'messages' list")
    messages = export["messages"]
    by_id = {m["id"]: m for m in messages if "id" in m}
    texts, replies, source_ids = [], [], []
    seen = set()
    stats = Counter(total_messages=len(messages))

    for message in messages:
        parent_id = message.get("reply_to_message_id")
        if parent_id is None:
            continue
        stats["explicit_replies"] += 1
        # Cross-chat references must not accidentally match a local message ID.
        peer = message.get("reply_to_peer_id")
        if peer is not None and str(peer) != str(export.get("id")):
            stats["skipped_cross_chat"] += 1
            continue
        parent = by_id.get(parent_id)
        if parent is None:
            stats["skipped_missing_parent"] += 1
            continue
        prompt = usable_text(parent, max_chars)
        response = usable_text(message, max_chars)
        if not prompt or not response:
            stats["skipped_unsuitable_text"] += 1
            continue
        text = normalize_for_search(prompt)
        key = (text, normalize_for_search(response))
        if key in seen:
            stats["skipped_duplicate_pair"] += 1
            continue
        seen.add(key)
        texts.append(text)
        replies.append(response)
        source_ids.append([parent_id, message["id"]])

    stats["accepted_pairs"] = len(texts)
    return {
        "schema_version": 1,
        "texts": texts,
        "replies": replies,
        "source_message_ids": source_ids,
        "stats": dict(stats),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-chars", type=int, default=1000)
    args = parser.parse_args()
    if args.max_chars < 1:
        parser.error("--max-chars must be positive")
    input_path = args.input
    if input_path is None:
        candidates = [
            p for p in TRAINING_DIR.glob("*.json")
            if p.resolve() not in {DEFAULT_OUTPUT.resolve(), args.output.resolve()}
        ]
        if len(candidates) != 1:
            parser.error("Provide an input path: expected exactly one chat export")
        input_path = candidates[0]
    if input_path.resolve() == args.output.resolve():
        parser.error("Output must differ from the original export")
    with input_path.open(encoding="utf-8-sig") as stream:
        dataset = prepare_training_data(json.load(stream), args.max_chars)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        json.dump(dataset, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    # Print counts only, never private conversation content.
    print(json.dumps(dataset["stats"], indent=2))
    print(f"Saved dataset to {args.output}")


if __name__ == "__main__":
    main()
