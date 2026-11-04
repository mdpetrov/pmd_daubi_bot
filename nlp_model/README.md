# TF-IDF reply retrieval

Run from the project root (Python 3.10+):

```powershell
python -m pip install -r nlp_model/requirements.txt
python nlp_model/prepare_training_data.py
python nlp_model/train_tfidf.py
```

Preparation reads the sole chat export in `.secret/nlp_model/training_data` and writes
`prepared_tfidf.json`. Training reads that prepared dataset and writes
`.secret/nlp_model/tfidf.joblib`. Both commands also accept an explicit input
path and `-o OUTPUT`. Training supports `--word-features` and `--char-features`
to adjust the vocabulary caps (defaults: 30,000 and 50,000).

The model combines word unigrams/bigrams (60%) with character fragments of
3–5 characters (40%). Sparse float32 matrices limit memory use. Training prints
pair counts, vocabulary sizes, index bytes, artifact size and elapsed time;
index bytes do not include Python objects or vocabulary memory.

Try the saved artifact without changing the bot:

```python
import joblib
from nlp_model.train_tfidf import search

model = joblib.load(".secret/nlp_model/tfidf.joblib")
matches = search(model, "Кто сегодня играет?", top_k=3, threshold=0.25)
for match in matches:
    print(match["score"], match["reply"])
```

Load once at startup, then reuse. An empty result means no acceptable match.
Scores measure lexical similarity, not confidence; the threshold needs manual
evaluation. This retrieves historical answers, rather than generating new text.
No held-out conversational quality score is claimed by training.

For deployment, copy the artifact and the `nlp_model` Python folder. Install
the same dependency versions on the server as on the training machine; capture
them with `python -m pip freeze > .secret/nlp_model/runtime-requirements.txt`
in the training environment. No original chat export is needed on the server.
The artifact contains private chat text: keep it private and load only trusted
joblib files, because loading them can execute Python code.

Tests: `python -m unittest discover -s tests -p "test_*tfidf.py"` and
`python -m unittest discover -s tests -p test_prepare_training_data.py`.

## Bot integration on Ubuntu

The bot loads the artifact once at startup. It uses the same response
probabilities for ordinary messages and direct replies. It draws one random
number per eligible message and skips retrieval when that number exceeds 0.5.

| Retrieval result | Response probability | Answer |
| --- | --- | --- |
| Best score >= 0.75 | 50% | Random distinct answer from all matches >= 0.75 |
| Best score < 0.75 or retrieval unavailable | 5% | Existing random phrase |

Each actual search starts a five-second cooldown per chat, even if no answer
is sent or search fails. The 5% phrase probability also applies when there are
no matches, the search is on cooldown, the model is disabled or unavailable,
or the search fails.
The bot's own messages and replies to polls sent by any bot are excluded from
free speech. Polls, commands, and maintenance continue independently.
Model answers are sent as Telegram replies to the triggering message.

### Prepare training data from the bot's message archive

The bot appends conversation text received in groups and supergroups to one UTF-8
JSONL file per chat under `.secret/data/chat_messages/`. Each line preserves the
Telegram message ID, timestamp, original text, and same-chat reply ID when
available. The archive omits sender IDs and names as separate fields. It skips
private chats, commands, senders Telegram marks as bots, and non-text messages.
Capture also includes older messages delivered after a polling delay. Telegram
controls which group messages the bot receives through its permissions and
privacy mode.

Run preparation on one chat archive at a time. The existing filters keep
explicit text replies with an archived parent. The archive flags forwarded text
so preparation can exclude it from training.

```powershell
python nlp_model/prepare_training_data.py .secret/data/chat_messages/-1001234567890.jsonl
python nlp_model/train_tfidf.py
```

The `.secret` directory is ignored by Git. The original message text can still
contain personal information.

### Update an existing model incrementally

Run the updater periodically on the host that stores the archive and model,
using the bot's OS account and Python environment. Use the archive whose filename
matches `TFIDF_CHAT_ID`. The initial model must come from the same chat.

```bash
python nlp_model/update_tfidf.py .secret/data/chat_messages/-1001234567890.jsonl
```

Use `--model PATH` for a model outside `.secret/nlp_model/tfidf.joblib`. The
updater scans the archive so new replies can reference older messages, adds
only new normalized prompt/reply pairs, and reports how many it appended. It
records the archive's chat ID on the first append and checks it on later runs.
The updater leaves the existing artifact in place when there are no new pairs
or the archive cannot be read, including if a live append leaves a partial line.
Retry after the archive write completes.

The updater uses an OS-held lock on a persistent sibling `.lock` file. An
overlapping invocation exits with an error and can run again later. Schedule
full refits separately from incremental updates.
On a successful run that appended pairs, restart the bot to load the new
artifact. A successful run reporting zero pairs needs no restart.

Only new prompts are vectorized. The fitted vocabulary and IDF values stay
fixed, so newly appearing terms may contribute no features. A separate full
refit is needed to learn new terms or refresh the IDF weights.

### Deploy the bot with retrieval enabled

Set `TFIDF_CHAT_ID` to the Telegram group ID whose history trained the model
(the actual Bot API chat ID, typically starting with `-100`, not a username or
the positive ID in an export). Retrieval is disabled without this setting and
never runs in other groups. The bot uses a fixed score cutoff of 0.75.

Copy the updated `main.py`, `pmd_daubi_bot/phrase_operation.py`,
`pmd_daubi_bot/reply_retrieval.py`, `pmd_daubi_bot/chat_message_store.py`, and
`nlp_model/` to the server. Keep the artifact already trained on Ubuntu.
Install `nlp_model/requirements.txt` into
the bot's existing venv if needed.

Run `sudo systemctl edit YOUR_SERVICE.service` and add:

```ini
[Service]
Environment="TFIDF_CHAT_ID=-100YOUR_GROUP_ID"
```

Replace the example service name and chat ID, then run:

```bash
sudo systemctl daemon-reload
sudo systemctl restart YOUR_SERVICE.service
sudo systemctl status YOUR_SERVICE.service --no-pager
```

The bot's `.secret/log/0.log` reports whether the model loaded. To try replies in
the configured group, send a few messages more than five seconds apart. To disable retrieval,
remove the `TFIDF_CHAT_ID` environment setting and restart the service.
