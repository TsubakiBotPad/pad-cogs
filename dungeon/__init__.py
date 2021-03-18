import asyncio

from .dungeoncog import DungeonCog


def setup(bot):
    n = DungeonCog(bot)
    bot.add_cog(n)
    asyncio.create_task(n.load_emojis())
