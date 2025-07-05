path = {"text_phrases": "./.secret/input/text_phrases.csv", 
        "token": "./.secret/token/.token", 
        "log_dir": "./.secret/log", 
        "data_dir": "./.secret/data",
        "readycheck_phrases": "./.secret/input/readycheck_phrases.csv"}
param_value = {'readycheck_cd': 15 * 60,
               'readycheck_default_phrase': 'Объявите время гейминга!'}
weight = {'base': .5,
          'increase': .1,
          'lifo_flg': True}
