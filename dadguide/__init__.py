from .dadguide import *

def setup(bot):
    n = Dadguide(bot)
    bot.add_cog(n)
    n.register_tasks()

__all__ = list(globals())