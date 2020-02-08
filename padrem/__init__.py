from .padrem import *

def setup(bot):
    n = PadRem(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reload_padrem())