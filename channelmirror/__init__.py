from .channelmirror import ChannelMirror

__red_end_user_data_statement__ = "No personal data is stored."


def setup(bot):
    n = ChannelMirror(bot)
    bot.add_cog(n)
