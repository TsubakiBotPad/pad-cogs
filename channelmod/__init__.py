from .channelmod import *

__red_end_user_data_statement__ = "No personal data is stored."

def setup(bot):
    n = ChannelMod(bot)
    bot.add_cog(n)
