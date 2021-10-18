from .crud import Crud

__red_end_user_data_statement__ = "User email addresses are stored persistently."


def setup(bot):
    bot.add_cog(Crud(bot))
