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

path = {'text_phrases': './.secret/input/text_phrases.csv',
        'token': './.secret/token/.token',
        'log_dir': './.secret/log',
        'data_dir': './.secret/data'}

if not os.path.isfile(path['text_phrases']):
    raise OSError('text_phrases not found')

with open(path['token'], 'rt', encoding='utf8') as fp:
	token = fp.read()

bot = telebot.TeleBot(token, threaded=False)

global_params = {}

random.seed(datetime.datetime.now().timestamp())

def write_log(chat_id, text):
    with open(os.path.join(path['log_dir'], f'{chat_id}.log'), mode='a') as log_con:
        log_con.write(f'{datetime.datetime.now()}: {text}\n')

def send_message(chat_id, text, params, sleep=0.5, **kwargs):
	''' Send a message with certain delay '''
	interval = time.time() - params['last_time_message_sent']
	if (interval < sleep):
		time.sleep(sleep - interval)
	message = bot.send_message(chat_id, text, **kwargs)
	params['last_time_message_sent'] = time.time()
	return message

def random_phrase(chat_id):
    with open(path['text_phrases'], mode='rt', encoding='utf-8') as con:
        write_log(chat_id, ': Load phrases')
        phrases = pd.read_csv(con, sep=';')
        phrase = phrases['phrase'].sample(n=1, weights=phrases['weight']).tolist()[0]
        write_log(chat_id, f'{phrase}')
        return phrase
    
def set_local_params(params:dict):
    ''' Creates empty dict with params for new session '''
    params.update({'last_time_message_sent':0,
                    'last_time_message_received':time.time(),
                    'last_ready_check':0})
    
@bot.message_handler(commands=['ready_check'], chat_types=['private', 'group', 'supergroup'], func=lambda m: (time.time() - m.date <= 10))
def get_message_readycheck(message):
    global global_params
    local_params = global_params.setdefault(message.chat.id, {})
    if len(local_params) == 0:
        set_local_params(local_params)
    write_log(message.chat.id, 'Trying to perform a ready check')
    readycheck_cd = 60 * 60
    cur_time = time.time()
    write_log(message.chat.id, print(local_params))
    time_diff = cur_time - local_params['last_ready_check']
    time_remain = readycheck_cd - time_diff
    if time_remain > 0:
        text = f'Ready Check Cooldown: {round(time_remain / 60,0)} min'
    else:
        chat_members = ['@' + member.user.username for member in bot.get_chat_administrators(message.chat.id) if member.user.is_bot == False]
        text = f'Объявите время гейминга! {" ".join(chat_members)}'
        # text = 'Объявите время гейминга! @alexanderkabadzha @idynnn @TkEgor @maxpetrov @Filanka @iskander_tarkinsky @Aquamarine_Eyes @mndche @msvst @van_de @elina_zak @a_dymchenko'
    send_message(message.chat.id, text=text, params=local_params)
    local_params['last_ready_check'] = cur_time
    global_params[message.chat.id] = local_params

@bot.message_handler(commands=['start'], chat_types=['private'], func=lambda m: (time.time() - m.date <= 10))
def get_message_start(message):
    global global_params
    local_params = global_params.setdefault(message.chat.id, {})
    if len(local_params) == 0:
        set_local_params(local_params)
    send_message(message.chat.id, text='ДАУБИ БОТ', params=local_params)
    start_text = '''Список команд:
/start - вывести стартовое сообщение
/ready_check - Провести проверку готовности
/add_phrase "название фразы" - добавить фразу (пока не работает)
'''
    send_message(message.chat.id, text=start_text, params=local_params)
    global_params[message.chat.id] = local_params

@bot.message_handler(commands=['add_phrase'], chat_types=['private'], func=lambda m: (time.time() - m.date <= 5))
def get_message_add_phrase(message):
    global global_params
    local_params = global_params.setdefault(message.chat.id, {})
    text = message.text 
    text = text.replace('/add_phrase ', '')
    text = text.replace('"', '')
    
    

@bot.message_handler(chat_types=['group', 'supergroup'], content_types=['text'], func=lambda m: (time.time() - m.date <= 10))
def get_message_group(message):
    global global_params
    local_params = global_params.setdefault(message.chat.id, {})
    if len(local_params) == 0:
        set_local_params(local_params)

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
    global_params[message.chat.id] = local_params
    write_log(message.chat.id, f'{local_params}')
    
    local_params['last_time_message_received'] = time.time()
        
if __name__ == '__main__':
    while True:
        try:
            write_log(0, 'Restart the bot')
            bot.polling(none_stop=True, interval=1) #обязательная для работы бота часть
        except Exception as e:
            write_log(0, 'Error in execution')
            write_log(0, e)
            time.sleep(10*60) #10 minutes