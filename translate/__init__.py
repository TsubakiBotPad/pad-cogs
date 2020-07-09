from .translate import Translate


def setup(bot):
    n=Translate(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.build_service())
