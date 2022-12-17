from .pipelineui import PipelineUI

__red_end_user_data_statement__ = "No personal data is stored."


async def setup(bot):
    pdb = PipelineUI(bot)
    bot.add_cog(pdb) if not __import__('asyncio').iscoroutinefunction(bot.add_cog) else await bot.add_cog(pdb)
