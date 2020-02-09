from .translate import Translate


def setup(bot):
    # TODO: Test
    bot.add_cog(Translate(bot))
