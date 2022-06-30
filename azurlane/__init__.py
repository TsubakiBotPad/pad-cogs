from .azurlane import AzurLane

__red_end_user_data_statement__ = "No personal data is stored."


async def setup(bot):
    n = AzurLane(bot)
    bot.add_cog(n) if not __import__('asyncio').iscoroutinefunction(bot.add_cog) else await bot.add_cog(n)
    bot.loop.create_task(n.register_menu())
    bot.loop.create_task(n.reload_al())
