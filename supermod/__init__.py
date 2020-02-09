from .supermod import *
import warnings

def setup(bot):
    warnings.warn("supermod is borked (and obsolete)")
    return
    n = SuperMod(bot)
    bot.loop.create_task(n.refresh_supermod())
    bot.add_listener(n.log_message, "on_message")
    bot.add_listener(n.no_thinking, "on_message")
    bot.add_cog(n)