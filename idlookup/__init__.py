from .idlookup import Idlookup

__red_end_user_data_statement__ = "Channels that idlookup is enabled are stored persistantly."


def setup(bot):
    bot.add_cog(Idlookup(bot))