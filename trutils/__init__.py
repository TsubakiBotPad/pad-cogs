from .trutils import *

__red_end_user_data_statement__ = "No personal data is stored."

def setup(bot):
    bot.add_cog(TrUtils(bot))
