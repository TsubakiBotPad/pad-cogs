from .damagecalc import *

def setup(bot):
    n = DamageCalc(bot)
    bot.add_cog(n)