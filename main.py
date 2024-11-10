import telebot
from telebot import types 
from telebot.util import quick_markup
import random
import datetime
import time
import json
import os
import numpy as np
import pandas as pd
import re

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Custom packages

import pmd_daubi_bot as pdb
from pmd_daubi_bot import config
# from pmd_daubi_bot.params_operation import ParamsOperations
# from pmd_daubi_bot.log_operation import LogOperations
# from pmd_daubi_bot.bot_operation import BotOperations

path = config.path
# Open bot
with open(path['token'], 'rt', encoding='utf8') as fp:
	token = fp.read()

bot = telebot.TeleBot(token, threaded=False)

PS = pdb.ParamsOperations(config)
LO = pdb.LogOperations(config)
BO = pdb.BotOperations(bot)



# if not os.path.isfile(path['text_phrases']):
    # raise OSError('text_phrases not found')




random.seed(datetime.datetime.now().timestamp())

    
    
@bot.message_handler(commands=['ready_check'], chat_types=['group', 'supergroup'], func=lambda m: (time.time() - m.date <= 10))
def get_message_readycheck(message):
    local_params = load_params(message.chat.id)
    readycheck_cd = config.param_value['readycheck_cd']
    
    write_log(message.chat.id, 'Trying to perform a ready check')
    cur_time = time.time()
    write_log(message.chat.id, local_params)
    time_diff = cur_time - local_params['last_ready_check']
    time_remain = readycheck_cd - time_diff
    if time_remain > 0:
        text = f'Ready Check Cooldown: {int(time_remain / 60)} min'
    else:
        chat_members = ['@' + member.user.username for member in bot.get_chat_administrators(message.chat.id) if member.user.is_bot == False]
        text = f'Объявите время гейминга! {" ".join(chat_members)}'
        # text = 'Объявите время гейминга! @alexanderkabadzha @idynnn @TkEgor @maxpetrov @Filanka @iskander_tarkinsky @Aquamarine_Eyes @mndche @msvst @van_de @elina_zak @a_dymchenko'
    send_message(message.chat.id, text=text, params=local_params)
    local_params['last_ready_check'] = cur_time
    save_params(message.chat.id, local_params)

@bot.message_handler(commands=['start'], chat_types=['private'], func=lambda m: (time.time() - m.date <= 10))
def get_message_start(message):
    local_params = load_params(message.chat.id)
    send_message(message.chat.id, text='ДАУБИ БОТ', params=local_params)
    start_text = '''Список команд:
/start - вывести стартовое сообщение
/ready_check - Провести проверку готовности
/add_phrase "название фразы" - добавить фразу (пока не работает)
'''
    send_message(message.chat.id, text=start_text, params=local_params)
    save_params(message.chat.id, local_params)

@bot.message_handler(commands=['add_phrase'], chat_types=['private'], func=lambda m: (time.time() - m.date <= 5))
def get_message_add_phrase(message):
    if len(local_params) == 0:
        set_local_params(local_params)
    send_message(message.chat.id, text='Введи фразу', params=local_params)
    save_params(message.chat.id, local_params)
    
    

@bot.message_handler(chat_types=['group', 'supergroup'], content_types=['text'], func=lambda m: (time.time() - m.date <= 10))
def get_message_group(message):
    local_params = load_params(message.chat.id)

    to_send = False
    rand = random.random()
    write_log(message.chat.id, f': Random = {round(rand, 2)}')
    
    if time.time() - local_params['last_time_message_received'] >= 60 * 60 * 5:
        write_log(message.chat.id, f": Last time sent: {local_params['last_time_message_received']}")
        to_send = True
        
    if rand <= 0.04:
        to_send = True
    if to_send:
        phrase = random_phrase(message.chat.id)
        send_message(message.chat.id, text=phrase, params=local_params, sleep=0.5)
    write_log(message.chat.id, f'{local_params}')
    
    local_params['last_time_message_received'] = time.time()
    save_params(message.chat.id, local_params)
        
if __name__ == '__main__':
    while True:
        try:
            write_log(0, 'Restart the bot')
            bot.polling(none_stop=True, interval=1) #обязательная для работы бота часть
        except Exception as e:
            write_log(0, 'Error in execution')
            write_log(0, e)
            time.sleep(10*60) #10 minutes