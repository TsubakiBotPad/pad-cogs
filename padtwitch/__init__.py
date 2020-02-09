from .padtwitch import *

def setup(bot):
    # TODO: I have no idea how to test this
    n = PadTwitch(bot)
    asyncio.get_event_loop().create_task(n.on_connect())
    bot.add_cog(n)