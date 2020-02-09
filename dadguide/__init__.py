from .dadguide import *
 

def setup(bot):
    n = Dadguide(bot)
    bot.add_cog(n)
    n.bot.loop.create_task(n.reload_data_task())
