# pmd_daubi_bot

This is a telegram bot which sometimes sends random messages to a group chat it's in. 
Currently working from: `main.py`

`/ready_poll` creates a non-anonymous readiness poll with the default answers
and lets participants add their own answer options directly in Telegram.
The bot pins the poll after creation; it needs permission to pin messages.
Pins expire at the next 07:00 UTC after creation. Expired polls are unpinned
lazily on the next group text message or readiness command; failed removals
are retried on later activity. Poll tracking survives bot restarts.
Requires pyTelegramBotAPI 4.35.0 or newer; upgrade existing installations with
`python -m pip install -r requirements.txt`.

## Configuration

Set these environment variables for the bot. The path variables are required by
the current configuration and should point to locations the bot's OS account can
read or write as needed.

| Variable | Required | Purpose |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token. |
| `BOT_PATH_TEXT_PHRASES` | Yes | Path to the bot's text phrases JSON file. |
| `BOT_PATH_LOG_DIR` | Yes | Directory for bot logs. Created if it does not exist. |
| `BOT_PATH_DATA_DIR` | Yes | Directory for bot data, including per-chat message archives. Created if it does not exist. |
| `BOT_PATH_READYCHECK_PHRASES` | Yes | Path to the ready-check phrases CSV file. |
| `BOT_PATH_RESPONSE_KEYWORDS` | Yes | Path to the response keywords JSON file. |
| `TFIDF_MODEL_PATH` | Optional, to run TF-IDF | Path to the trained TF-IDF model file, such as `tfidf.joblib`. Used by both the bot and `update_tfidf.py`. |
| `TFIDF_PREPARED_PATH` | Optional, to prepare or train TF-IDF | Full path, including filename, for the prepared dataset JSON, such as `prepared_tfidf.json`. The preparation script also looks for default JSON inputs in a `training_data` directory beside this file. |
| `TFIDF_CHAT_ID` | Optional, to enable TF-IDF replies | Telegram group ID whose messages the bot may use for TF-IDF retrieval. Retrieval is disabled if this is unset. |

Use absolute paths in the service environment so behavior does not depend on
the process's working directory. Keep the model and chat archives private.
