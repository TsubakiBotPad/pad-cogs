from .padmonitor import *

def setup(bot):
    n = PadMonitor(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.check_seen_loop())
