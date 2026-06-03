path = {"text_phrases": "./.secret/input/text_phrases/text_phrases.json",
        "token": "./.secret/token/.token",
        "log_dir": "./.secret/log",
        "data_dir": "./.secret/data",
        "readycheck_phrases": "./.secret/input/readycheck_phrases.csv",
        "response_keywords": "./.secret/input/response_keywords.json"}

param_value = {'readycheck_cd': 15 * 60,
               'readycheck_default_phrase': 'Объявите время гейминга!',
               # Looking for play (LFP) feature configuration
               'lfp_close_before_minutes': 15,
               'lfp_check_interval_seconds': 30,
               'lfp_people_limit': 30,
               'lfp_callback_prefix': 'lfp',
               'lfp_button_labels': {
                   'join': 'Иду',
                   'leave': 'Не иду',
                   'close': 'Закрыть'
               },
               'lfp_usage_hint': (
                   'Как создать сбор: /lfp <время> <минимум> [максимум]\n'
                   'Примеры:\n'
                   '/lfp 21:30 3 — нужно 3+ игрока\n'
                   '/lfp 21:30 3 5 — строго от 3 до 5 игроков\n'
                   '/lfp in 90 3 5 — игра через 90 минут'
               )}

weight = {'base': .5,
          'increase': .1,
          'lifo_flg': True}
