from .seniority import *

__red_end_user_data_statement__ = "Activity data is stored."

def setup(bot):
    n = Seniority(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.init())
