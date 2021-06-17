import asyncio

from .dungeoncog import DungeonCog


def setup(bot):
    n = DungeonCog(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.register_menu())
    asyncio.create_task(n.load_emojis())
