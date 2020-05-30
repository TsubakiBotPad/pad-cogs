import warnings

from .padevents import *


def setup(bot):
    #FIXME
    warnings.warn("PadEvents is borked.")
    return
    n = PadEvents(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reload_padevents())
    bot.loop.create_task(n.check_started())
