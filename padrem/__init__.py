from .padrem import *
import warnings

def setup(bot):
    warnings.warn("PadRem is borked.")
    return
    n = PadRem(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reload_padrem())