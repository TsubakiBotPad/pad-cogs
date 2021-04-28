from .padinfo import PadInfo

__red_end_user_data_statement__ = "No personal data is stored."


def setup(bot):
    n = PadInfo(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.register_menu())
    bot.loop.create_task(n.reload_nicknames())
