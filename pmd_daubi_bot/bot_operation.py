import time

class BotOperations(object):
    def __init__(self, bot):
        self.bot = bot
        # self.config = config
    def send_message(self, chat_id, text, params, sleep=0.5, **kwargs):
        ''' Send a message with certain delay '''
        bot = self.bot
        interval = time.time() - params['last_time_message_sent']
        if (interval < sleep):
            time.sleep(sleep - interval)
        message = bot.send_message(chat_id, text, **kwargs)
        params['last_time_message_sent'] = time.time()
        
        return message
