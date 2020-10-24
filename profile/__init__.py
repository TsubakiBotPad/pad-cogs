from .profile import Profile

__red_end_user_data_statement__ = "Profile data is stored persistantly."


def setup(bot):
    bot.add_cog(Profile(bot))
