from .memes import *

__red_end_user_data_statement__ = "All stored data is anonymized."

def setup(bot):
    bot.add_cog(Memes(bot))
