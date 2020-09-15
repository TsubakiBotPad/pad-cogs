from .azurelane import *

__red_end_user_data_statement__ = "No personal data is stored."


def setup(bot):
    n = AzureLane(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reload_al())
