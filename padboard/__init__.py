from .padboard import *

__red_end_user_data_statement__ = "No personal data is stored persistantly."

def setup(bot):
    bot.add_cog(PadBoard(bot))
