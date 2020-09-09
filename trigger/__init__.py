from .trigger import Trigger

__red_end_user_data_statement__ = "Triggers are stored persistantly."

def setup(bot):
    n = Trigger(bot)
    bot.loop.create_task(n.save_stats())
    bot.loop.create_task(n.load_triggers())
    bot.add_cog(n)
