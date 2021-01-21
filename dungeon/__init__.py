from .dungeoncog import DungeonCog


def setup(bot):
    n = DungeonCog(bot)
    bot.add_cog(n)