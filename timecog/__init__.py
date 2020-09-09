from .timecog import *

__red_end_user_data_statement__ = "Reminders are stored."

def setup(bot):
    n = TimeCog(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reminderloop())
