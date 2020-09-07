from .calculator import *

__red_end_user_data_statement__ = "The most recent answer in each channel is stored."

def setup(bot):
    bot.add_cog(Calculator(bot))
