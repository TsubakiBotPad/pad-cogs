from .padevents import PadEvents

__red_end_user_data_statement__ = "No personal data is stored."


def setup(bot):
    n = PadEvents(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reload_padevents())
    bot.loop.create_task(n.check_started())
