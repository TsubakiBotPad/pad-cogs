from .globalban import GlobalBan


def setup(bot):
    bot.add_cog(GlobalBan(bot))
