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
