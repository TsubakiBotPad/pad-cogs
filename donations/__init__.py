from .donations import *


def setup(bot):
    n = Donations(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.set_server_attributes())
