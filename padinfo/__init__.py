from .padinfo import PadInfo

def setup(bot):
    n = PadInfo(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reload_nicknames())