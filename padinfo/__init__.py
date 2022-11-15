import json
from pathlib import Path

from .padinfo import PadInfo

with open(Path(__file__).parent / "info.json") as file:
    __red_end_user_data_statement__ = json.load(file)['end_user_data_statement']


async def setup(bot):
    n = PadInfo(bot)
    bot.add_cog(n) if not __import__('asyncio').iscoroutinefunction(bot.add_cog) else await bot.add_cog(n)
    bot.loop.create_task(n.register_menu())
    bot.loop.create_task(n.reload_nicknames())
    bot.loop.create_task(n.load_aliases())
