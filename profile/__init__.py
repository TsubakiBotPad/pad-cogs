from .profile import Profile

__red_end_user_data_statement__ = "Profile data is stored persistantly."


async def setup(bot):
    bot.add_cog(Profile(bot)) if not __import__('asyncio').iscoroutinefunction(bot.add_cog) else await bot.add_cog(Profile(bot))
