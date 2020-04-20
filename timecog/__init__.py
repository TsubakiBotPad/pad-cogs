from .timecog import *


def setup(bot):
    n = TimeCog(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reminderloop())
