from .channelmod import *


def setup(bot):
    n = ChannelMod(bot)
    bot.add_cog(n)
