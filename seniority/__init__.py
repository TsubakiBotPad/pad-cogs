from .seniority import *

def setup(bot):
    n = Seniority(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.init())