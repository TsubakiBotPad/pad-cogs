from .translate import Translate

__red_end_user_data_statement__ = "No personal data is stored."

def setup(bot):
    n=Translate(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.build_service())
