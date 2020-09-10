from .sqlactivitylog import *

__red_end_user_data_statement__ = "All message edits/deletions less than 3 weeks old are saved."

def setup(bot):
    n = SqlActivityLogger(bot)
    bot.add_cog(n)
