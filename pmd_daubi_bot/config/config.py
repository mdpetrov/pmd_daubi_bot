import os
from pathlib import Path

path = {
    "text_phrases": os.getenv("BOT_PATH_TEXT_PHRASES", "./.secret/input/text_phrases/text_phrases.json"), 
    "token": os.getenv("BOT_PATH_TOKEN", "./.secret/token/.token"), 
    "log_dir": os.getenv("BOT_PATH_LOG_DIR", "./.secret/log"), 
    "data_dir": os.getenv("BOT_PATH_DATA_DIR", "./.secret/data"),
    "readycheck_phrases": os.getenv("BOT_PATH_READYCHECK_PHRASES", "./.secret/input/readycheck_phrases.csv"),
    "response_keywords": os.getenv("BOT_PATH_RESPONSE_KEYWORDS", "./.secret/input/response_keywords.json")
}

Path(path['log_dir']).mkdir(parents=True, exist_ok=True)
Path(path['data_dir']).mkdir(parents=True, exist_ok=True)

param_value = {'readycheck_cd': 5 * 60,
               'readycheck_default_phrase': 'Объявите время гейминга!',
               # /ready_poll poll text
               'readypoll_question': 'Буду играть сегодня?',
               'readypoll_options': ['Да', 'Нет', 'Возможно'],
               # Looking for play (LFP) feature configuration
               'lfp_quorum_default': 5,
               'lfp_quorum_min': 1,
               'lfp_quorum_max': 5,
               'lfp_callback_prefix': 'lfp',
               'lfp_button_labels': {
                   'yes': 'Да',
                   'no': 'Нет',
                   'earlier': 'Раньше',
                   'later': 'Позже',
                   'close': 'Закрыть'
               },
               'lfp_usage_hint': '/looking_for_play <time> [quorum]; time: HH[:MM] | in MM | in HH:MM'}
weight = {'base': .5,
          'increase': .1,
          'lifo_flg': True}
