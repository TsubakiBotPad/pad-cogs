bot_ref = None


def set_bot_ref(ref):
    global bot_ref
    bot_ref = ref


def get_bot():
    return bot_ref
