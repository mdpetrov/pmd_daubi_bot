import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import time
import os
import logging
from datetime import datetime

# Custom packages

from pmd_daubi_bot.config import config
from pmd_daubi_bot.params_operation import ParamsOperations
from pmd_daubi_bot.log_operation import LogOperations
from pmd_daubi_bot.bot_operation import BotOperations
from pmd_daubi_bot.phrase_operation import PhraseOperations

from pmd_daubi_bot.lfp_helpers import (
    lfp_parse_time_and_quorum,
    lfp_build_keyboard,
    lfp_render_text,
    lfp_update_vote,
    lfp_prune_and_autoclose,
    lfp_post_summary,
)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

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


random.seed(datetime.now().timestamp())


@bot.message_handler(commands=['start'], chat_types=['private'], func=lambda m: (time.time() - m.date <= 10))
def get_message_start(message):
    # Track user in chat
    local_params = PO.load_params(message.chat.id)
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
    user_group_chats = PO.get_user_group_chats(message.from_user.id)
    if not user_group_chats:
        BO.send_message(message.chat.id, text='Ошибка: ты не состоишь ни в одной группе, где работает бот. Фразы можно добавлять только в групповые чаты.', params=local_params)
        return
    BO.send_message(message.chat.id, text='''Ты можешь добавить новую фразу в генератор ответов. 
Фразы добавляются анонимно.''', params=local_params)
    markup = InlineKeyboardMarkup()
    for chat_id, chat_name in user_group_chats.items():
        callback_data = f"phrase_chat:{chat_id}"
        markup.add(InlineKeyboardButton(text=str(chat_name), callback_data=callback_data))
    BO.send_message(message.chat.id, text='Выбери группу для добавления фразы:', params=local_params, reply_markup=markup)
    
    PO.save_params(message.chat.id, local_params)

def check_phrase(message, target_chat_id):
    local_params = PO.load_params(message.chat.id)
    if message.text:
        phrase = message.text
        BO.send_message(message.chat.id, text=f'Добавить фразу? (Да/Нет): "{phrase}"', params=local_params)
        bot.register_next_step_handler(message, add_phrase, phrase=phrase, target_chat_id=target_chat_id)
        PO.save_params(message.chat.id, local_params)

def add_phrase(message, phrase, target_chat_id):
    local_params = PO.load_params(message.chat.id)
    if message.text:
        answer = message.text.strip()
        if answer.lower() not in ['да', 'нет']:
            BO.send_message(message.chat.id, text='Я не понял твой ответ. Начни заново.', params=local_params)
        elif answer.lower() in ['нет']:
            BO.send_message(message.chat.id, text='Нет, так нет.', params=local_params)
        elif answer.lower() in ['да']:
            # Verify user still has access to the selected chat
            user_group_chats = PO.get_user_group_chats(message.from_user.id)
            if not user_group_chats or target_chat_id not in user_group_chats:
                BO.send_message(message.chat.id, text='Ошибка: ты не состоишь в выбранной группе, где работает бот. Фразы можно добавлять только в групповые чаты.', params=local_params)
            else:
                BO.send_message(message.chat.id, text='ПОЕХАЛИ', params=local_params)
                result = PhO.add_phrase(phrase=phrase, chat_id=target_chat_id)
                BO.send_message(message.chat.id, text=result, params=local_params)
        else:
            raise ValueError('Cannot understand users answer')
    PO.save_params(message.chat.id, local_params)
    
@bot.message_handler(commands=['ready_check'], chat_types=['group', 'supergroup'], func=lambda m: (time.time() - m.date <= 10))
def get_message_readycheck(message):
    # Track user in chat
    PO.update_user_chat(message.from_user.id, message.chat)
    local_params = PO.load_params(message.chat.id)
    readycheck_cd = config.param_value['readycheck_cd']
    
    LO.write_log(message.chat.id, 'Trying to perform a ready check')
    cur_time = time.time()
    LO.write_log(message.chat.id, local_params)
    time_diff = cur_time - local_params['last_ready_check']
    time_remain = readycheck_cd - time_diff
    if time_remain >= 60:
        text = f'Ready Check Cooldown: {int(time_remain / 60)} min'
    elif time_remain > 0:
        text = f'Ready Check Cooldown: {int(time_remain)} sec'
    else:
        chat_members = []
        for member in bot.get_chat_administrators(message.chat.id):
            if not member.user.is_bot:
                if member.user.username:
                    chat_members.append(f'@{member.user.username}')
                else:
                    chat_members.append(f'<a href="tg://user?id={member.user.id}">{member.user.first_name}</a>')
        text = PhO.random_readycheck_phrase(chat_id=message.chat.id)
        text = f'{text} {" ".join(chat_members)}'
        local_params['last_ready_check'] = cur_time
        # text = f'Объявите время гейминга! {" ".join(chat_members)}'
    BO.send_message(message.chat.id, text=text, params=local_params, parse_mode='HTML')
    PO.save_params(message.chat.id, local_params)
    
@bot.message_handler(commands=['looking_for_play', 'lfp'], chat_types=['group', 'supergroup'], func=lambda m: (time.time() - m.date <= 10))
def get_message_lfp(message):
    # Track user in chat
    PO.update_user_chat(message.from_user.id, message.chat)
    LO.write_log(chat_id=message.chat.id, text=f"LFP command received from user {message.from_user.id} ({getattr(message.from_user, 'username', None)})")
    local_params = PO.load_params(message.chat.id)
    LO.write_log(chat_id=message.chat.id, text="Loaded local_params for LFP")
    lfp_prune_and_autoclose(bot, BO, PO, LO, message.chat.id, local_params, config.param_value)
    LO.write_log(chat_id=message.chat.id, text="Pruned and autoclosing expired LFP sessions if any")
    args_text = message.text.split(maxsplit=1)
    args_text = args_text[1] if len(args_text) > 1 else ''
    LO.write_log(chat_id=message.chat.id, text=f"Parsed args_text for LFP: '{args_text}'")
    target_ts, time_str, quorum = lfp_parse_time_and_quorum(args_text, time.time(), config.param_value)
    LO.write_log(chat_id=message.chat.id, text=f"lfp_parse_time_and_quorum result: target_ts={target_ts}, time_str={time_str}, quorum={quorum}")
    if target_ts is None:
        LO.write_log(chat_id=message.chat.id, text="LFP time parsing failed, sending usage hint")
        BO.send_message(message.chat.id, text=config.param_value['lfp_usage_hint'], params=local_params)
        PO.save_params(message.chat.id, local_params)
        return

    session = {
        'session_id': '',
        'chat_id': message.chat.id,
        'message_id': 0,
        'creator_id': message.from_user.id,
        'time_str': time_str,
        'time_ts': target_ts,
        'quorum': quorum,
        'created_ts': time.time(),
        'closed': False,
        'votes': {'yes':{}, 'no':{}, 'earlier':{}, 'later':{}}
    }
    LO.write_log(chat_id=message.chat.id, text=f"Created new LFP session: {session}")
    text = lfp_render_text(session)
    msg = BO.send_message(
        message.chat.id,
        text=text,
        params=local_params,
        parse_mode='HTML',
        reply_markup=lfp_build_keyboard(session, config.param_value)
    )
    LO.write_log(chat_id=message.chat.id, text=f"LFP message sent, message_id={msg.message_id}")
    session['message_id'] = msg.message_id
    session['session_id'] = f"{message.chat.id}_{msg.message_id}"
    # Rebuild keyboard with real session_id
    bot.edit_message_reply_markup(
        chat_id=message.chat.id,
        message_id=msg.message_id,
        reply_markup=lfp_build_keyboard(session, config.param_value)
    )
    LO.write_log(chat_id=message.chat.id, text=f"Edited message reply markup for LFP session_id={session['session_id']}")
    # Pin the vote message (may require admin rights)
    try:
        bot.pin_chat_message(chat_id=message.chat.id, message_id=msg.message_id, disable_notification=True)
        LO.write_log(chat_id=message.chat.id, text=f"Pinned LFP message_id={msg.message_id}")
    except Exception as e:
        LO.write_log(chat_id=message.chat.id, text=f"Failed to pin LFP message: {e}")
    # Save session
    if 'lfp_sessions' not in local_params:
        local_params['lfp_sessions'] = {}
    local_params['lfp_sessions'][session['session_id']] = session
    LO.write_log(chat_id=message.chat.id, text=f"Saved LFP session to local_params under session_id={session['session_id']}")
    PO.save_params(message.chat.id, local_params)
    LO.write_log(chat_id=message.chat.id, text="Params saved after LFP session creation")

@bot.message_handler(chat_types=['group', 'supergroup'], content_types=['text'], func=lambda m: (time.time() - m.date <= 10))
def get_message_group(message):
    # Track user in chat
    PO.update_user_chat(message.from_user.id, message.chat)
    # Lazy auto-close expired LFP sessions on any group text
    local_params = PO.load_params(message.chat.id)
    lfp_prune_and_autoclose(bot, BO, PO, LO, message.chat.id, local_params, config.param_value)
    PO.save_params(message.chat.id, local_params)
    # Reload to continue normal processing with freshest params
    local_params = PO.load_params(message.chat.id)
    responded = False
    
    # Handle replies to bot messages
    if message.reply_to_message:
        if message.reply_to_message.from_user.username == 'daubi2_bot':
            # Use phrase operations to analyze reply and get response
            message_sent = PhO.analyze_reply_to_bot(message.text, chat_id=message.chat.id)
            LO.write_log(chat_id=message.chat.id, text='Reply to bot detected')
            if message_sent is not None:
                LO.write_log(chat_id=message.chat.id, text=f'Responding to reply: {message_sent}')
                BO.send_message(message.chat.id, text=message_sent, params=local_params, sleep=0.5, reply_to_message_id=message.id)
                responded = True
            else:
                LO.write_log(chat_id=message.chat.id, text='Ignoring reply (5% chance)')

    # Handle regular messages (not replies)
    if not responded:
        # Use phrase operations to analyze message and decide response
        should_respond, response_reason, response_phrase = PhO.analyze_message_and_decide_response(
        message.text, 
        message.chat.id, 
        local_params['last_time_message_received']
        )   
    
        # Log the decision
        rand_val = random.random()
        LO.write_log(chat_id=message.chat.id, text=f'Regular message - Random = {round(rand_val, 2)}, Should respond: {should_respond}, Reason: {response_reason}')
        
        if should_respond:
            LO.write_log(chat_id=message.chat.id, text=f'Responding to regular message: {response_phrase}')
            BO.send_message(message.chat.id, text=response_phrase, params=local_params, sleep=0.5)
    
    local_params['last_time_message_received'] = time.time()
    PO.save_params(message.chat.id, local_params)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith('phrase_chat:'))
def handle_phrase_chat_selection(call):
    """Handle chat selection callback when adding a phrase"""
    # Track user in chat
    chat_id = call.message.chat.id
    local_params = PO.load_params(chat_id)
    
    # Parse callback data: phrase_chat:<target_chat_id>
    data = call.data.split(':')
    if len(data) != 2:
        bot.answer_callback_query(call.id, 'Техническая ошибка')
        return
    
    target_chat_id = data[1]
    
    # Verify user has access to this chat
    user_group_chats = PO.get_user_group_chats(call.from_user.id)
    if not user_group_chats or target_chat_id not in user_group_chats:
        LO.write_log(0, f'Error while trying to add phrase.\n\tUser_group_chats: {user_group_chats}.\tTarget_chat_id: {target_chat_id}')
        bot.answer_callback_query(call.id, 'Ошибка: нет доступа к этой группе')
        return
    
    # Answer the callback query
    bot.answer_callback_query(call.id, f'Выбрана группа: {target_chat_id}')
    
    # Edit the message to show selection
    bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
    
    # Request phrase input
    BO.send_message(chat_id, text='Введи фразу для добавления:', params=local_params)
    bot.register_next_step_handler(call.message, check_phrase, target_chat_id=target_chat_id)
    PO.save_params(chat_id, local_params)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith(config.param_value['lfp_callback_prefix']+':'))
def handle_lfp_callback(call):
    # Track user in chat
    PO.update_user_chat(call.from_user.id, call.message.chat)
    chat_id = call.message.chat.id
    local_params = PO.load_params(chat_id)
    lfp_prune_and_autoclose(bot, BO, PO, LO, chat_id, local_params, config.param_value)
    data = call.data.split(':')
    if len(data) != 3:
        bot.answer_callback_query(call.id, 'Ошибка')
        return
    _, action, session_id = data
    sessions = local_params.get('lfp_sessions', {})
    session = sessions.get(session_id)
    if not session:
        bot.answer_callback_query(call.id, 'Сессия не найдена')
        return
    if session.get('closed'):
        bot.answer_callback_query(call.id, 'Сессия закрыта')
        return
    # Auto-close if time passed
    if session['time_ts'] <= time.time():
        session['closed'] = True
        sessions[session_id] = session
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=session['message_id'], reply_markup=None)
        bot.unpin_chat_message(chat_id=chat_id, message_id=session['message_id'])
        lfp_post_summary(BO, PO, LO, chat_id, session)
        local_params['lfp_sessions'] = sessions
        PO.save_params(chat_id, local_params)
        bot.answer_callback_query(call.id, 'Сессия закрыта')
        return

    user_tag = lfp_update_vote(session, call.from_user)
    if action == 'yes':
        session['votes']['yes'][call.from_user.id] = user_tag
        bot.answer_callback_query(call.id, 'Голос учтён')
    elif action == 'no':
        session['votes']['no'][call.from_user.id] = user_tag
        bot.answer_callback_query(call.id, 'Голос учтён')
    elif action == 'earlier':
        session['votes']['earlier'][call.from_user.id] = user_tag
        bot.answer_callback_query(call.id, 'Голос учтён')
    elif action == 'later':
        session['votes']['later'][call.from_user.id] = user_tag
        bot.answer_callback_query(call.id, 'Голос учтён')
    elif action == 'close':
        session['closed'] = True
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=session['message_id'], reply_markup=None)
        bot.unpin_chat_message(chat_id=chat_id, message_id=session['message_id'])
        lfp_post_summary(BO, PO, LO, chat_id, session)
        bot.answer_callback_query(call.id, 'Закрыто')
    else:
        bot.answer_callback_query(call.id, 'Неизвестное действие')
    # Update rendered text
    bot.edit_message_text(lfp_render_text(session), chat_id=chat_id, message_id=session['message_id'], parse_mode='HTML', reply_markup=lfp_build_keyboard(session, config.param_value) if not session['closed'] else None)
    # Persist
    sessions[session_id] = session
    local_params['lfp_sessions'] = sessions
    PO.save_params(chat_id, local_params)
        
if __name__ == '__main__':
    LO.write_log(0, 'Start the bot')        
    bot.polling(none_stop=True, interval=1) #обязательная для работы бота 