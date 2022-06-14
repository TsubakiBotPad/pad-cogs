from .padle import PADle

__red_end_user_data_statement__ = "Guess data for PADles played is saved."


async def setup(bot):
    n = PADle(bot)
    bot.add_cog(n) if not __import__('asyncio').iscoroutinefunction(bot.add_cog) else await bot.add_cog(n)
    bot.loop.create_task(n.register_menu())
