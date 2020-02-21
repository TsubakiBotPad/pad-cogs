from .sqlactivitylog import *


def setup(bot):
    n = SqlActivityLogger(bot)
    bot.add_cog(n)
