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
import logging

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Custom packages

from pmd_daubi_bot.config import config
from pmd_daubi_bot.params_operation import ParamsOperations
from pmd_daubi_bot.log_operation import LogOperations
from pmd_daubi_bot.bot_operation import BotOperations
from pmd_daubi_bot.phrase_operation import PhraseOperations

path = config.path
# Open bot
with open(path['token'], 'rt', encoding='utf8') as fp:
	token = fp.read()

bot = telebot.TeleBot(token, threaded=False)

PO = ParamsOperations(config=config)
LO = LogOperations(config=config)
BO = BotOperations(bot=bot)
PhO = PhraseOperations(config=config)

LOG_FILENAME = '.secret/log/0.log'
logging.basicConfig(filename=LOG_FILENAME, level=logging.INFO)

# if not os.path.isfile(path['text_phrases']):
    # raise OSError('text_phrases not found')


random.seed(datetime.datetime.now().timestamp())

    
    

@bot.message_handler(commands=['start'], chat_types=['private'], func=lambda m: (time.time() - m.date <= 10))
def get_message_start(message):
    local_params = PO.load_params(message.chat.id)
    # BO.send_message(message.chat.id, text='ДАУБИ БОТ', params=local_params)
    start_text = '''ДАУБИ БОТ 
Список команд:
    /start - вывести стартовое сообщение
    /ready_check - Провести проверку готовности (только в групповых чатах)
    /add_phrase - Добавить фразу (только в ЛС)
'''
    BO.send_message(message.chat.id, text=start_text, params=local_params)
    PO.save_params(message.chat.id, local_params)

@bot.message_handler(commands=['add_phrase'], chat_types=['private'], func=lambda m: (time.time() - m.date <= 5))
def get_message_add_phrase(message):
    local_params = PO.load_params(message.chat.id)
    BO.send_message(message.chat.id, text='''Ты можешь добавить новую фразу в генератор ответов. 
Фразы добавляются анонимно. 
Введи фразу:''', params=local_params)
    bot.register_next_step_handler(message, check_phrase)
    PO.save_params(message.chat.id, local_params)

def check_phrase(message):
    local_params = PO.load_params(message.chat.id)
    if message.text:
        phrase = message.text
        BO.send_message(message.chat.id, text=f'Добавить фразу? (Да/Нет): "{phrase}"', params=local_params)
        bot.register_next_step_handler(message, add_phrase, phrase=phrase)
        PO.save_params(message.chat.id, local_params)

def add_phrase(message, phrase):
    local_params = PO.load_params(message.chat.id)
    if message.text:
        answer = message.text.strip()
        if answer.lower() not in ['да', 'нет']:
            BO.send_message(message.chat.id, text=f'Я не понял твой ответ. Начни заново.', params=local_params)
        elif answer.lower() in ['нет']:
            BO.send_message(message.chat.id, text=f'Нет, так нет.', params=local_params)
        elif answer.lower() in ['да']:
            BO.send_message(message.chat.id, text=f'ПОЕХАЛИ', params=local_params)
            result = PhO.add_phrase(phrase=phrase)
            BO.send_message(message.chat.id, text=result, params=local_params)
        else:
            raise ValueError('Cannot understand users answer')
    PO.save_params(message.chat.id, local_params)
    
@bot.message_handler(commands=['ready_check'], chat_types=['group', 'supergroup'], func=lambda m: (time.time() - m.date <= 10))
def get_message_readycheck(message):
    local_params = PO.load_params(message.chat.id)
    readycheck_cd = config.param_value['readycheck_cd']
    
    LO.write_log(message.chat.id, 'Trying to perform a ready check')
    cur_time = time.time()
    LO.write_log(message.chat.id, local_params)
    time_diff = cur_time - local_params['last_ready_check']
    time_remain = readycheck_cd - time_diff
    if time_remain > 0:
        text = f'Ready Check Cooldown: {int(time_remain / 60)} min'
    else:
        chat_members = ['@' + member.user.username for member in bot.get_chat_administrators(message.chat.id) if member.user.is_bot == False]
        text = PhO.random_readycheck_phrase(chat_id=message.chat.id)
        text = f'{text} {" ".join(chat_members)}'
        # text = f'Объявите время гейминга! {" ".join(chat_members)}'
    BO.send_message(message.chat.id, text=text, params=local_params)
    local_params['last_ready_check'] = cur_time
    PO.save_params(message.chat.id, local_params)

@bot.message_handler(chat_types=['group', 'supergroup'], content_types=['text'], func=lambda m: (time.time() - m.date <= 10))
def get_message_group(message):
    local_params = PO.load_params(message.chat.id)
    
    if message.reply_to_message.from.username == 'daubi2_bot':
        BO.send_message(message.chat.id, text='Ну без негатива же...', params=local_params, sleep=0.5)
    
    to_send = False
    rand = random.random()
    LO.write_log(chat_id=message.chat.id, text=f': Random = {round(rand, 2)}')
    
    auto_send_cd_h = rand * (10 - 5) + 5 # gen cd [5,10] hrs
    if time.time() - local_params['last_time_message_received'] >= auto_send_cd_h * 3600:
        LO.write_log(message.chat.id, f": Last time sent: {local_params['last_time_message_received']}")
        to_send = True
        
    if rand <= 0.03:
        to_send = True
    if to_send:
        phrase = PhO.random_phrase(message.chat.id)
        BO.send_message(message.chat.id, text=phrase, params=local_params, sleep=0.5)
    LO.write_log(message.chat.id, f'{local_params}')
    
    local_params['last_time_message_received'] = time.time()
    PO.save_params(message.chat.id, local_params)
        
if __name__ == '__main__':
    while True:
        try:
            LO.write_log(0, 'Restart the bot')
            bot.polling(none_stop=True, interval=1) #обязательная для работы бота часть
        except Exception as e:
            LO.write_log(0, 'Error in execution')
            # LO.write_log(0, e)
            logging.basicConfig(level=logging.DEBUG)
            logging.error(e, exc_info=True)
            time.sleep(1*60) # 1 minute
            logging.basicConfig(level=logging.INFO)