from .seniority import *


def setup(bot):
    # TODO: Test this!
    n = Seniority(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.init())
