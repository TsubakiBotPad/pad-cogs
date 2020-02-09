from .streamcopy import *


def setup(bot):
    n = StreamCopy(bot)
    bot.add_listener(n.check_stream, "on_member_update")
    bot.loop.create_task(n.refresh_stream())
    bot.add_cog(n)
