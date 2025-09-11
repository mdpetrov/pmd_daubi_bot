import re
import time
from datetime import datetime, timedelta
from telebot import types


def lfp_format_user_tag(user):
    if user.username:
        return f"@{user.username}"
    else:
        first_name = user.first_name if user.first_name else "User"
        return f"<a href=\"tg://user?id={user.id}\">{first_name}</a>"


def lfp_parse_time_and_quorum(args_text: str, now_ts: float, param_value):
    """
    Parse time (absolute or relative) and optional quorum from args text.
    Time rules:
      - Absolute: HH[:MM]; if HH >= 12 -> 24h; if HH < 12 -> assume PM (HH += 12)
      - Relative: 'in MM' or 'in HH:MM'
      - If absolute time today has passed -> schedule for tomorrow
    Returns: (target_ts, time_str, quorum)
    """
    args = args_text.strip().split()
    if len(args) == 0:
        return None, None, None

    quorum_default = param_value['lfp_quorum_default']
    quorum_min = param_value['lfp_quorum_min']
    quorum_max = param_value['lfp_quorum_max']
    quorum = quorum_default
    if len(args) >= 2 and args[-1].isdigit():
        quorum = int(args[-1])
        args = args[:-1]
    quorum = max(quorum_min, min(quorum_max, quorum))

    now = datetime.fromtimestamp(now_ts)

    if len(args) >= 1 and args[0].lower() == 'in':
        if len(args) < 2:
            return None, None, None
        rel = args[1]
        if re.fullmatch(r"\d+", rel):
            minutes = int(rel)
            delta = timedelta(minutes=minutes)
        elif re.fullmatch(r"\d{1,2}:\d{1,2}", rel):
            hh, mm = rel.split(':')
            delta = timedelta(hours=int(hh), minutes=int(mm))
        else:
            return None, None, None
        target_dt = now + delta
        time_str = target_dt.strftime('%H:%M')
        return int(target_dt.timestamp()), time_str, quorum

    time_token = args[0]
    if re.fullmatch(r"\d{1,2}$", time_token):
        hh = int(time_token)
        mm = 0
    elif re.fullmatch(r"\d{1,2}:\d{1,2}$", time_token):
        hh, mm = map(int, time_token.split(':'))
    else:
        return None, None, None

    if hh >= 24 or mm >= 60:
        return None, None, None

    if hh < 12:
        hh = (hh + 12) % 24

    target_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target_dt <= now:
        target_dt = target_dt + timedelta(days=1)
    time_str = target_dt.strftime('%H:%M')
    return int(target_dt.timestamp()), time_str, quorum


def lfp_build_keyboard(session, param_value):
    labels = param_value['lfp_button_labels']
    prefix = param_value['lfp_callback_prefix']
    session_id = session['session_id']
    kb = types.InlineKeyboardMarkup(row_width=3)
    btn_yes = types.InlineKeyboardButton(labels['yes'], callback_data=f"{prefix}:yes:{session_id}")
    btn_no = types.InlineKeyboardButton(labels['no'], callback_data=f"{prefix}:no:{session_id}")
    btn_earlier = types.InlineKeyboardButton(labels['earlier'], callback_data=f"{prefix}:earlier:{session_id}")
    btn_later = types.InlineKeyboardButton(labels['later'], callback_data=f"{prefix}:later:{session_id}")
    btn_close = types.InlineKeyboardButton(labels['close'], callback_data=f"{prefix}:close:{session_id}")
    kb.add(btn_yes, btn_no, btn_close)
    kb.add(btn_earlier, btn_later)
    return kb


def lfp_render_text(session):
    time_str = session['time_str']
    votes = session['votes']
    def join_names(bucket):
        if len(bucket) == 0:
            return ''
        return ', '.join(bucket.values())
    yes_line = f"Да ({len(votes['yes'])}): {join_names(votes['yes'])}" if len(votes['yes'])>0 else f"Да (0)"
    earlier_line = f"Раньше ({len(votes['earlier'])}): {join_names(votes['earlier'])}" if len(votes['earlier'])>0 else f"Раньше (0)"
    later_line = f"Позже ({len(votes['later'])}): {join_names(votes['later'])}" if len(votes['later'])>0 else f"Позже (0)"
    no_line = f"Нет ({len(votes['no'])}): {join_names(votes['no'])}" if len(votes['no'])>0 else f"Нет (0)"
    header = f"Ищем гейминг на {time_str}. Голосуй:"
    return "\n".join([header, yes_line, earlier_line, later_line, no_line])


def lfp_update_vote(session, user):
    user_tag = lfp_format_user_tag(user)
    for k in ['yes','no','earlier','later']:
        if user.id in session['votes'][k]:
            del session['votes'][k][user.id]
    return user_tag


def lfp_post_summary(BO, PO, LO, chat_id, session):
    yes_votes = session['votes']['yes']
    quorum = session['quorum']
    time_str = session['time_str']
    yes_count = len(yes_votes)
    if yes_count >= quorum:
        yes_tags = ', '.join(yes_votes.values()) if yes_votes else ''
        text = f"Гейминг в {time_str}. {yes_tags}"
    else:
        text = f"Не хватает людей. Кворум: {quorum}, Да: {yes_count}."
    BO.send_message(chat_id, text=text, params=PO.load_params(chat_id), reply_to_message_id=session['message_id'], parse_mode='HTML')


def lfp_prune_and_autoclose(bot, BO, PO, LO, chat_id, params, param_value):
    sessions = params.get('lfp_sessions', {})
    now_ts = time.time()
    for sid, sess in list(sessions.items()):
        if not sess.get('closed') and sess.get('time_ts', 0) <= now_ts:
            sess['closed'] = True
            sessions[sid] = sess
            lfp_post_summary(BO, PO, LO, chat_id, sess)
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=sess['message_id'], reply_markup=None)
            bot.unpin_chat_message(chat_id=chat_id, message_id=sess['message_id'])
    params['lfp_sessions'] = sessions


