import html
import re
import time
from datetime import datetime, timedelta, timezone

from telebot import types


LFP_ACTION_JOIN = 'join'
LFP_ACTION_LEAVE = 'leave'
LFP_ACTION_CLOSE = 'close'
LFP_CLOSE_REASON_TIME = 'time'
LFP_CLOSE_REASON_FULL = 'full'
LFP_CLOSE_REASON_MANUAL = 'manual'
MSK_TZ = timezone(timedelta(hours=3), name='MSK')


def lfp_datetime_from_ts(ts):
    return datetime.fromtimestamp(ts, MSK_TZ)


def lfp_format_datetime(dt):
    return dt.strftime('%d.%m %H:%M МСК')


def _format_minutes(seconds):
    minutes = max(0, int(seconds // 60))
    if minutes == 0:
        return 'меньше минуты'
    return f'{minutes} мин.'


def lfp_format_user_tag(user):
    if getattr(user, 'username', None):
        return f"@{html.escape(user.username)}"
    first_name = getattr(user, 'first_name', None) or 'Игрок'
    return f'<a href="tg://user?id={user.id}">{html.escape(first_name)}</a>'


def _parse_time_tokens(args, now_ts):
    if not args:
        return None, None, None, 'Укажи время игры.'

    now = lfp_datetime_from_ts(now_ts)
    if args[0].lower() == 'in':
        if len(args) < 2:
            return None, None, None, 'После "in" укажи количество минут или формат ЧЧ:ММ.'
        rel = args[1]
        if re.fullmatch(r'\d+', rel):
            delta = timedelta(minutes=int(rel))
        elif re.fullmatch(r'\d{1,2}:\d{1,2}', rel):
            hours, minutes = map(int, rel.split(':'))
            if minutes >= 60:
                return None, None, None, 'В относительном времени минуты должны быть от 0 до 59.'
            delta = timedelta(hours=hours, minutes=minutes)
        else:
            return None, None, None, 'Не понял относительное время. Пример: /lfp in 90 3 5.'
        target_dt = now + delta
        return int(target_dt.timestamp()), lfp_format_datetime(target_dt), args[2:], None

    time_token = args[0]
    if re.fullmatch(r'\d{1,2}', time_token):
        hours = int(time_token)
        minutes = 0
    elif re.fullmatch(r'\d{1,2}:\d{1,2}', time_token):
        hours, minutes = map(int, time_token.split(':'))
    else:
        return None, None, None, 'Не понял время. Пример: /lfp 21:30 3 5.'

    if hours >= 24 or minutes >= 60:
        return None, None, None, 'Время должно быть в формате ЧЧ:ММ.'

    target_dt = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    if target_dt <= now:
        target_dt += timedelta(days=1)
    return int(target_dt.timestamp()), lfp_format_datetime(target_dt), args[1:], None


def lfp_parse_request(args_text, now_ts, param_value):
    args = args_text.strip().split()
    target_ts, time_str, rest, error = _parse_time_tokens(args, now_ts)
    if error:
        return None, error

    if not rest:
        return None, 'Укажи кворум: одно число для формата 3+ или два числа для диапазона 3 5.'
    if len(rest) > 2 or not all(re.fullmatch(r'\d+', item) for item in rest):
        return None, 'Кворум должен быть одним или двумя числами. Пример: /lfp 21:30 3 5.'

    min_people = int(rest[0])
    max_people = int(rest[1]) if len(rest) == 2 else None
    people_limit = param_value.get('lfp_people_limit', 30)
    if min_people < 1:
        return None, 'Минимум игроков должен быть больше нуля.'
    if max_people is not None and max_people < min_people:
        return None, 'Максимум игроков не может быть меньше минимума.'
    if max_people is not None and max_people > people_limit:
        return None, f'Максимум игроков не должен быть больше {people_limit}.'

    close_before_minutes = param_value['lfp_close_before_minutes']
    close_ts = target_ts - close_before_minutes * 60
    if close_ts <= now_ts:
        earliest_start = lfp_datetime_from_ts(now_ts + close_before_minutes * 60)
        return None, (
            f'До игры должно быть больше {close_before_minutes} мин., иначе сбор сразу закроется.\n'
            f'Ближайшее допустимое время старта: {lfp_format_datetime(earliest_start)}.'
        )

    return {
        'start_ts': target_ts,
        'time_str': time_str,
        'close_ts': int(close_ts),
        'close_before_minutes': close_before_minutes,
        'min_people': min_people,
        'max_people': max_people,
    }, None


def lfp_create_session(chat_id, message_id, creator, parsed, now_ts):
    session_id = f'{chat_id}_{int(now_ts * 1000)}_{creator.id}'
    creator_id = str(creator.id)
    attendees = {
        creator_id: {
            'user_id': creator.id,
            'tag': lfp_format_user_tag(creator),
        }
    }
    return {
        'version': 2,
        'active': True,
        'session_id': session_id,
        'chat_id': chat_id,
        'message_id': message_id,
        'creator_id': creator.id,
        'created_ts': int(now_ts),
        'closed_ts': None,
        'close_reason': None,
        'start_ts': parsed['start_ts'],
        'time_str': parsed['time_str'],
        'close_ts': parsed['close_ts'],
        'close_before_minutes': parsed['close_before_minutes'],
        'min_people': parsed['min_people'],
        'max_people': parsed['max_people'],
        'attendees': attendees,
        'declined': {},
    }


def lfp_get_active_session(params):
    session = params.get('lfp_session')
    if session and session.get('version') == 2 and session.get('active') and not session.get('closed_ts'):
        return session
    return None


def lfp_store_session(params, session):
    params['lfp_session'] = session


def lfp_clear_old_sessions(params):
    params['lfp_sessions'] = {}


def lfp_quota_text(session):
    min_people = session['min_people']
    max_people = session.get('max_people')
    if max_people is None:
        return f'{min_people}+'
    if min_people == max_people:
        return str(min_people)
    return f'{min_people}-{max_people}'


def lfp_count_text(session):
    count = len(session.get('attendees', {}))
    max_people = session.get('max_people')
    if max_people is None:
        return f'{count}/{session["min_people"]}+'
    return f'{count}/{max_people}'


def lfp_user_lines(users):
    if not users:
        return ['пока никого']
    return [item['tag'] for item in users.values()]


def lfp_attendee_lines(session):
    return lfp_user_lines(session.get('attendees', {}))


def lfp_declined_lines(session):
    return lfp_user_lines(session.get('declined', {}))


def lfp_render_text(session, now_ts=None):
    now_ts = now_ts or time.time()
    status = 'идет сбор'
    if session.get('closed_ts'):
        status = 'закрыт'
    elif session.get('max_people') is not None and len(session.get('attendees', {})) >= session['max_people']:
        status = 'набран максимум'

    close_in = _format_minutes(session['close_ts'] - now_ts)
    attendee_text = '\n'.join([f'- {line}' for line in lfp_attendee_lines(session)])
    declined_text = '\n'.join([f'- {line}' for line in lfp_declined_lines(session)])
    return (
        f'Сбор на игру\n\n'
        f'Время: {session["time_str"]}\n'
        f'Кворум: {lfp_quota_text(session)}\n'
        f'Идут: {lfp_count_text(session)}\n'
        f'Статус: {status}\n'
        f'Закроется за {session["close_before_minutes"]} мин. до старта '
        f'(примерно через {close_in})\n\n'
        f'Идут:\n{attendee_text}\n\n'
        f'Не идут ({len(session.get("declined", {}))}):\n{declined_text}'
    )


def lfp_render_existing_session_notice(session):
    return (
        f'В этом чате уже есть активный сбор на {session["time_str"]}.\n'
        f'Идут: {lfp_count_text(session)}\n'
        f'Новый сбор можно создать после закрытия текущего.'
    )


def lfp_render_final_summary(session):
    count = len(session.get('attendees', {}))
    min_people = session['min_people']
    reason = session.get('close_reason')
    if reason == LFP_CLOSE_REASON_FULL:
        title = 'Сбор закрыт: набран максимум игроков.'
    elif reason == LFP_CLOSE_REASON_MANUAL:
        title = 'Сбор закрыт вручную.'
    else:
        title = 'Сбор закрыт: время подтверждения закончилось.'

    if count >= min_people:
        result = 'Игра состоится.'
    else:
        result = 'Игроков не хватает.'

    attendee_text = '\n'.join([f'- {line}' for line in lfp_attendee_lines(session)])
    declined_text = '\n'.join([f'- {line}' for line in lfp_declined_lines(session)])
    return (
        f'{title}\n\n'
        f'Время: {session["time_str"]}\n'
        f'Кворум: {lfp_quota_text(session)}\n'
        f'Идут: {lfp_count_text(session)}\n'
        f'{result}\n\n'
        f'Идут:\n{attendee_text}\n\n'
        f'Не идут ({len(session.get("declined", {}))}):\n{declined_text}'
    )


def lfp_build_keyboard(session, param_value):
    prefix = param_value['lfp_callback_prefix']
    session_id = session['session_id']
    labels = param_value['lfp_button_labels']
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(
        types.InlineKeyboardButton(labels['join'], callback_data=f'{prefix}:{LFP_ACTION_JOIN}:{session_id}'),
        types.InlineKeyboardButton(labels['leave'], callback_data=f'{prefix}:{LFP_ACTION_LEAVE}:{session_id}'),
        types.InlineKeyboardButton(labels['close'], callback_data=f'{prefix}:{LFP_ACTION_CLOSE}:{session_id}'),
    )
    return kb


def lfp_add_attendee(session, user):
    attendees = session.setdefault('attendees', {})
    declined = session.setdefault('declined', {})
    user_id = str(user.id)
    max_people = session.get('max_people')
    if max_people is not None and user_id not in attendees and len(attendees) >= max_people:
        return False, 'Мест уже нет: набран максимум игроков.'
    declined.pop(user_id, None)
    attendees[user_id] = {
        'user_id': user.id,
        'tag': lfp_format_user_tag(user),
    }
    return True, 'Ты в списке.'


def lfp_remove_attendee(session, user):
    attendees = session.setdefault('attendees', {})
    declined = session.setdefault('declined', {})
    user_id = str(user.id)
    attendees.pop(user_id, None)
    declined[user_id] = {
        'user_id': user.id,
        'tag': lfp_format_user_tag(user),
    }
    return True, 'Ответ записан: не идешь.'


def lfp_close_reason(session, now_ts):
    if session.get('closed_ts'):
        return None
    max_people = session.get('max_people')
    if max_people is not None and len(session.get('attendees', {})) >= max_people:
        return LFP_CLOSE_REASON_FULL
    if now_ts >= session['close_ts']:
        return LFP_CLOSE_REASON_TIME
    return None


def lfp_finalize_session(session, reason, now_ts=None):
    session['active'] = False
    session['closed_ts'] = int(now_ts or time.time())
    session['close_reason'] = reason
    return session


def lfp_user_can_close(bot, chat_id, user_id, session):
    return user_id == session.get('creator_id')


def _safe_telegram_call(LO, log_chat_id, description, func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        LO.write_log(log_chat_id, f'LFP {description} failed: {e}')
        return None


def lfp_close_session(bot, BO, PO, LO, chat_id, params, session, reason):
    now_ts = time.time()
    lfp_finalize_session(session, reason, now_ts)
    lfp_store_session(params, session)
    PO.save_params(chat_id, params)

    _safe_telegram_call(
        LO,
        chat_id,
        'edit poll message on close',
        bot.edit_message_text,
        lfp_render_text(session, now_ts),
        chat_id=chat_id,
        message_id=session['message_id'],
        parse_mode='HTML',
        reply_markup=None,
    )
    _safe_telegram_call(
        LO,
        chat_id,
        'unpin poll message on close',
        bot.unpin_chat_message,
        chat_id=chat_id,
        message_id=session['message_id'],
    )
    _safe_telegram_call(
        LO,
        chat_id,
        'post final summary',
        BO.send_message,
        chat_id,
        text=lfp_render_final_summary(session),
        params=PO.load_params(chat_id),
        reply_to_message_id=session['message_id'],
        parse_mode='HTML',
    )
    return session


def lfp_prune_and_autoclose(bot, BO, PO, LO, chat_id, params, param_value):
    session = params.get('lfp_session')
    if not session or session.get('closed_ts') or not session.get('active'):
        return None

    reason = lfp_close_reason(session, time.time())
    if not reason:
        return None

    return lfp_close_session(bot, BO, PO, LO, chat_id, params, session, reason)
