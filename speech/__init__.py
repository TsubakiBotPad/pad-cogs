from .speech import Speech

def setup(bot):
    bot.add_cog(Speech(bot))
