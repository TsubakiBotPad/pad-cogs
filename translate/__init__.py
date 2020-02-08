from .translate import Translate

def setup(bot):
    bot.add_cog(Translate(bot))