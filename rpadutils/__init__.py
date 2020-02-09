from .rpadutils import *

def setup(bot):
    bot.add_cog(RpadUtils(bot))

__all__ = list(globals())