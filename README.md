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
