from .chronomagia import *

def setup(bot):
    n = ChronoMagia(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reload_cm_task())
