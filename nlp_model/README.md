# TF-IDF reply retrieval

Run from the project root (Python 3.10+):

```powershell
python -m pip install -r nlp_model/requirements.txt
python nlp_model/prepare_training_data.py
python nlp_model/train_tfidf.py
```

Preparation reads the sole chat export in `.secret/training_data` and writes
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

The bot loads the artifact once at startup. Direct replies to this bot always
receive an answer. For other messages it draws one random number, skips all
searches when that number exceeds 0.5, and reuses that same number below:

| Best score | Ordinary-message probability | Answer |
| --- | --- | --- |
| >= 0.75 | 50% | Random distinct answer from all matches >= 0.75 |
| >= 0.5 and < 0.75 | 10% | Random distinct answer from that band |
| < 0.5 or no match | 5% | Existing random phrase |

Each actual search starts a five-second cooldown per chat, even if no answer
is sent or search fails. During cooldown, missing-model, or disabled-chat
conditions, random phrases use 100% probability for direct replies to this bot
and 5% for ordinary messages. Other users' replies count as ordinary messages.
The bot's own messages and replies to polls sent by any bot are excluded from
free speech. Polls, commands, and maintenance continue independently.
Model answers are sent as Telegram replies to the triggering message.
Logs record the decision reason (probability gate, score band, cooldown,
no match, disabled model, or search error).

Set `TFIDF_CHAT_ID` to the Telegram group ID whose history trained the model
(the actual Bot API chat ID, typically starting with `-100`, not a username or
the positive ID in an export). Retrieval is disabled without this setting and
never runs in other groups. `TFIDF_THRESHOLD` is no longer used by the bot;
the decision bands above replace it.

Copy the updated `main.py`, `pmd_daubi_bot/phrase_operation.py`,
`pmd_daubi_bot/reply_retrieval.py`, and `nlp_model/` to the server. Keep the
artifact already trained on Ubuntu. Install `nlp_model/requirements.txt` into
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

The bot's `.secret/log/0.log` reports whether the model loaded. Test in the
configured group by replying directly to a bot message. To disable retrieval,
remove the `TFIDF_CHAT_ID` environment setting and restart the service.
