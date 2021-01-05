from .mycog import Mycog


def setup(bot):
    n = Mycog(bot)
    bot.add_cog(n)