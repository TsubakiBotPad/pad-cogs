import warnings

from .padevents import *


def setup(bot):
    n = PadEvents(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reload_padevents())
    bot.loop.create_task(n.check_started())
