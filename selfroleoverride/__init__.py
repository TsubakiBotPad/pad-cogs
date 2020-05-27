from .selfroleoverride import *


def setup(bot):
    pdb = SelfRoleOverride(bot)
    bot.add_cog(pdb)
