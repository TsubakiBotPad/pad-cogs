from .trigger import Trigger


def setup(bot):
    n = Trigger(bot)
    bot.loop.create_task(n.save_stats())
    bot.loop.create_task(n.load_triggers())
    bot.add_cog(n)
