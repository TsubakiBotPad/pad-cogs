from .sqlactivitylog import *


def setup(bot):
    n = SqlActivityLogger(bot)
    bot.add_cog(n)
    n.bot.loop.create_task(n.ongoing())
