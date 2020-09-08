from .donations import *

__red_end_user_data_statement__ = "This cog stores your custom commands."

def setup(bot):
    n = Donations(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.set_server_attributes())
