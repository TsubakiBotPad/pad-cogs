from .crud import Crud

__red_end_user_data_statement__ = "User email addresses are stored persistently."


async def setup(bot):
    bot.add_cog(Crud(bot)) if not __import__('asyncio').iscoroutinefunction(bot.add_cog) else await bot.add_cog(Crud(bot))
