from .azurelane import *

def setup(bot):
    n = AzureLane(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reload_al())