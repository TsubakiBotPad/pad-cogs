from .sqlactivitylog import *

def setup(bot):
    bot.add_cog(SqlActivityLogger(bot))