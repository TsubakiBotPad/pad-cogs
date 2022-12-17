from .crowddata import CrowdData

__red_end_user_data_statement__ = "All explicitly stored user preferences are kept persistantly."


async def setup(bot):
    bot.add_cog(CrowdData(bot)) if not __import__('asyncio').iscoroutinefunction(bot.add_cog) else await bot.add_cog(CrowdData(bot))
