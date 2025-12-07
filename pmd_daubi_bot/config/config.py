path = {"text_phrases": "./.secret/input/text_phrases/text_phrases.json", 
        "token": "./.secret/token/.token", 
        "log_dir": "./.secret/log", 
        "data_dir": "./.secret/data",
        "readycheck_phrases": "./.secret/input/readycheck_phrases.csv",
        "response_keywords": "./.secret/input/response_keywords.json"}
param_value = {'readycheck_cd': 15 * 60,
               'readycheck_default_phrase': 'Объявите время гейминга!',
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
