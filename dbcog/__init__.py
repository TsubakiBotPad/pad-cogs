from .dbcog import DBCog

__red_end_user_data_statement__ = "No personal data is stored."


def setup(bot):
    n = DBCog(bot)
    bot.add_cog(n)
    n.bot.loop.create_task(n.reload_data_task())
