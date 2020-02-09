from .schoolidol import *


def setup(bot):
    n = SchoolIdol(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reload_sif())
