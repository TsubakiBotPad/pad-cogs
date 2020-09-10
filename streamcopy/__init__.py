from .streamcopy import *

__red_end_user_data_statement__ = "No personal data is stored."

def setup(bot):
    n = StreamCopy(bot)
    bot.add_listener(n.check_stream, "on_member_update")
    bot.loop.create_task(n.refresh_stream())
    bot.add_cog(n)
