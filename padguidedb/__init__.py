from .padguidedb import *

__red_end_user_data_statement__ = "No personal data is stored."


def setup(bot):
    pdb = PadGuideDb(bot)
    bot.add_cog(pdb)
