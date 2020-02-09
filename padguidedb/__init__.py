from .padguidedb import *


def setup(bot):
    # TODO: Test this! I don't have the databases
    bot.add_cog(PadGuideDb(bot))
