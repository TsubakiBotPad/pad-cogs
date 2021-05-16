from .padglobal import PadGlobal

__red_end_user_data_statement__ = "No personal data is stored."


def setup(bot):
    n = PadGlobal(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.register_menu())
