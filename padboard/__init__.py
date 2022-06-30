from .padboard import PadBoard

__red_end_user_data_statement__ = "No personal data is stored persistantly."


async def setup(bot):
    bot.add_cog(PadBoard(bot)) if not __import__('asyncio').iscoroutinefunction(bot.add_cog) else await bot.add_cog(PadBoard(bot))
