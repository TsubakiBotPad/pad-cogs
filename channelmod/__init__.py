from .channelmod import *

def setup(bot):
    n = ChannelMod(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.channel_inactivity_monitor())