from .damagecalc import *

__red_end_user_data_statement__ = "No personal data is stored."

def setup(bot):
    n = DamageCalc(bot)
    bot.add_cog(n)
