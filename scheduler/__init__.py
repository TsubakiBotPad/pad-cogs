from .scheduler import *

def setup(bot):
    n = Scheduler(bot)
    bot.loop.create_task(n.queue_manager())
    bot.add_cog(n)
