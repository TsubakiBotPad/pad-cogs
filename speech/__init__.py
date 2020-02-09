from .speech import Speech


def setup(bot):
    # TODO: Test! I don't have an API!
    bot.add_cog(Speech(bot))
