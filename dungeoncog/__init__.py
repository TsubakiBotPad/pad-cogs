import json
from pathlib import Path

from .dungeoncog import DungeonCog

with open(Path(__file__).parent / "info.json") as file:
    __red_end_user_data_statement__ = json.load(file)['end_user_data_statement']


def setup(bot):
    n = DungeonCog(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.register_menu())
    bot.loop.create_task(n.load_emojis())
