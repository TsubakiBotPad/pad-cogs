from .twitter2 import *

def setup(bot):
    #TODO: Test this! I don't have the APIs
    n = TwitterCog2(bot)
    loop = asyncio.get_event_loop().create_task(n.connect())
    bot.add_cog(n)