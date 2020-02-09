from .statistics import *
import warnings

def setup(bot):
    warnings.warn("statistics is borked")
    return
    #TODO: This doesn't work.  At all.
    bot.add_cog(Statistics(bot))