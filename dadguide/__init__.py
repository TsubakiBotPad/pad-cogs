from .dadguide import *

__red_end_user_data_statement__ = "No personal data is stored."

def setup(bot):
    n = Dadguide(bot)
    bot.add_cog(n)
    n.bot.loop.create_task(n.reload_data_task())
