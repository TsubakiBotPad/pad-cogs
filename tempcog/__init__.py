from .tempcog import TempCog

__red_end_user_data_statement__ = "No personal data is stored."


async def setup(bot):
    n = TempCog(bot)
    await bot.add_cog(n)
