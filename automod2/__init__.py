from .automod2 import *

__red_end_user_data_statement__ = "This cog stores id of users manually marked as problematic."

def setup(bot):
    bot.add_cog(AutoMod2(bot))
