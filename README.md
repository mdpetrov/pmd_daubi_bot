# pmd_daubi_bot

This Telegram bot sometimes sends random messages to the group chats it belongs to.
The application entry point is `main.py`.

`/ready_poll` creates a non-anonymous readiness poll with the default answers
and lets participants add options directly in Telegram. The bot pins the poll
after creation and needs permission to pin messages. Pins expire at the next
07:00 UTC after creation. Expired polls are unpinned lazily on the next group
text message or readiness command; failed removals are retried later. Poll
tracking survives bot restarts.

Requires Python 3.10+ and pyTelegramBotAPI 4.35.0 or newer. Install project
dependencies from the project root:

```bash
python -m pip install -r requirements.txt
```

## Configuration

Set these environment variables for the bot. All listed path variables are
required by the current configuration. Use absolute paths and ensure the bot's
operating-system account has the necessary read/write permissions.

| Variable | Required | Purpose |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token. |
| `BOT_PATH_TEXT_PHRASES` | Yes | Path to the text phrases JSON file. |
| `BOT_PATH_LOG_DIR` | Yes | Directory for per-chat log files. The bot creates it if needed. |
| `BOT_PATH_DATA_DIR` | Yes | Bot data directory, including per-chat message archives. The bot creates it if needed. |
| `BOT_PATH_READYCHECK_PHRASES` | Yes | Path to the ready-check phrases CSV file. |
| `BOT_PATH_RESPONSE_KEYWORDS` | Yes | Path to the response keywords JSON file. |
| `TFIDF_MODEL_PATH` | Required for training, updating, and retrieval | Full path to the trained model artifact, such as `.../tfidf.joblib`. |
| `TFIDF_PREPARED_PATH` | Required for all NLP scripts and retrieval | Full path, including filename, for the prepared dataset, such as `.../prepared_tfidf.json`. The default source search directory is `<parent-of-prepared-file>/training_data`. |
| `TFIDF_CHAT_ID` | Required to enable retrieval | Telegram group ID whose history trained the model. If unset, TF-IDF retrieval is disabled. |

The TF-IDF path variables are required for the NLP scripts because they load
the shared bot configuration. This includes `TFIDF_PREPARED_PATH` for
`update_tfidf.py`, which imports the preparation module. All NLP scripts also
need `BOT_PATH_LOG_DIR` and `BOT_PATH_DATA_DIR` set because the configuration
creates those directories at import time. For the full bot, set all five
`BOT_PATH_*` variables. Keep the model and message archives private: both
contain chat text.

## Logging

Python application logs go to stderr, which systemd captures in the journal.
View them with:

```bash
journalctl -u YOUR_SERVICE.service -f
```

Bot operations logged with a valid chat ID are written to
`<BOT_PATH_LOG_DIR>/<chat_id>.log`. General logs, including startup and
TF-IDF model load status, appear in the journal. The bot no longer writes to
`0.log`; an old file, if present, is left untouched.

## TF-IDF reply retrieval

The retrieval model returns historical replies based on lexical similarity; it
does not generate new text. It combines word unigrams and bigrams (60%) with
character fragments of 3–5 characters (40%). Sparse float32 matrices limit
memory use. Training reports pair counts, vocabulary sizes, sparse index bytes,
artifact size, and elapsed time. Index bytes do not include Python objects or
vocabulary memory.

### Prepare training data and train the model

The bot appends group and supergroup text messages to one UTF-8 JSONL archive per
chat at `<BOT_PATH_DATA_DIR>/chat_messages/<chat_id>.jsonl`. Records include the
Telegram message ID, timestamp, original text, and same-chat reply ID when
available; sender IDs and names are not recorded separately. The bot skips
private chats, commands, bot senders, and non-text messages. Telegram's group
permissions and privacy mode control which messages the bot receives.

Prepare one chat archive at a time. In an interactive shell, export or source
the same environment variables configured for the service, or replace the
variables in the examples below with literal paths. A systemd `Environment=`
setting is not automatically available in an interactive shell. Preparation
keeps explicit text replies
whose parent is present in the archive. It excludes forwarded text, unsuitable
or oversized messages, and duplicate normalized prompt/reply pairs. For example,
from the project root:

```bash
python nlp_model/prepare_training_data.py "$BOT_PATH_DATA_DIR/chat_messages/$TFIDF_CHAT_ID.jsonl"
python nlp_model/train_tfidf.py
```

The prepared JSON is written to `TFIDF_PREPARED_PATH`; training reads that file
and writes the model to `TFIDF_MODEL_PATH`. Both scripts accept explicit input
paths and `-o OUTPUT` to override their configured defaults. Training also
accepts `--word-features` and `--char-features` to change the vocabulary caps
(defaults: 30,000 and 50,000).

If no source is passed to `prepare_training_data.py`, it expects exactly one
JSON export in `<parent-of-TFIDF_PREPARED_PATH>/training_data`.
Passing a JSONL archive path explicitly is recommended for bot archives.

### Incrementally update the existing model

For routine updates to the same chat, run the updater against that chat's
archive:

```bash
python nlp_model/update_tfidf.py "$BOT_PATH_DATA_DIR/chat_messages/$TFIDF_CHAT_ID.jsonl"
```

The archive filename stem must match the model's chat ID after the first append.
The initial model must have been trained from that same chat. The updater scans
the full archive so new replies may refer to older parent messages, but appends
only new normalized prompt/reply pairs. It prints the number appended and keeps
the existing artifact unchanged when there are no new pairs or the archive
cannot be read. If a live archive write leaves a partial final line, retry once
the write has completed.
Pass `--model PATH` to override `TFIDF_MODEL_PATH` for this command; `--max-chars`
changes the maximum prompt/reply length accepted during preparation (default:
1,000 characters).

An OS-held lock on a sibling `.lock` file prevents overlapping updates. After an
update appends pairs, restart the bot to load the updated artifact. No restart is
needed when zero pairs were appended.

Incremental updates use the existing vectorizers, vocabulary, and IDF weights.
New terms outside the fitted vocabulary cannot contribute features. Run the
prepare and train commands for a full refit that learns new terms or refreshes
IDF weights. Schedule full refits separately from incremental updates.

### Bot retrieval behavior

Set `TFIDF_CHAT_ID` to the Telegram Bot API group ID whose archive trained the
model (typically starts with `-100`; use the actual chat ID, not a username or
the positive ID from a Telegram export). Retrieval is restricted to that chat.
The bot loads `TFIDF_MODEL_PATH` once at startup and uses a fixed score cutoff of
0.75.

| Retrieval result | Ordinary-message probability | Direct-reply probability | Answer |
| --- | --- | --- | --- |
| Best score >= 0.75 | 50% | 100% | Random distinct answer from all matches >= 0.75 |
| Best score < 0.75 or retrieval unavailable | 5% | 100% | Existing random phrase |

Each actual search starts a five-second cooldown per chat, even if no answer is
sent or search fails. Direct replies receive an existing random phrase when
there are no qualifying matches, the search is on cooldown, retrieval is
disabled or unavailable, or search fails. Ordinary messages use that fallback
with 5% probability. The bot's own messages and replies to polls sent by any
bot are excluded from free speech. Polls, commands, and maintenance continue
independently. Model answers are sent as Telegram replies to the triggering
message.

### Deploy and verify

Install the project requirements in the bot's environment and deploy the
`nlp_model/` code with the trained model artifact. Configure all required
environment variables in the systemd service or its environment file; for
example:

```ini
[Service]
Environment="TFIDF_CHAT_ID=-100YOUR_GROUP_ID"
```

The service must also define the required path variables and
`TELEGRAM_BOT_TOKEN`. Then reload and restart it:

```bash
sudo systemctl daemon-reload
sudo systemctl restart YOUR_SERVICE.service
sudo systemctl status YOUR_SERVICE.service --no-pager
journalctl -u YOUR_SERVICE.service -f
```

The journal reports whether the TF-IDF model loaded. To disable retrieval, unset
`TFIDF_CHAT_ID` and restart the service.

### Try the model manually

```python
import joblib
from nlp_model.train_tfidf import search

model = joblib.load("/path/to/tfidf.joblib")
matches = search(model, "Кто сегодня играет?", top_k=3, threshold=0.25)
for match in matches:
    print(match["score"], match["reply"])
```

Load the artifact once and reuse it. An empty result means no acceptable match.
Scores measure lexical similarity, not confidence; the search threshold needs
manual evaluation. Training does not claim a held-out conversational quality
score. Load only trusted `joblib` files because deserialization can execute
Python code.

## Tests

Run the TF-IDF and source-preparation tests from the project root:

```bash
python -m unittest discover -s tests -p "test_*tfidf.py"
python -m unittest discover -s tests -p test_prepare_training_data.py
```
