import asyncio

from redbot.core import commands
from uvicorn import Server, Config

from .api import app
from .botref import set_bot_ref


class APICog(commands.Cog):
    server: Server

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        set_bot_ref(bot)

    async def entrypoint(self):
        config = Config(app, host="0.0.0.0", port=80, log_level="info")
        self.server = Server(config=config)
        await asyncio.create_task(self.server.serve())

    async def cog_unload(self) -> None:
        self.server.should_exit = True
        self.server.force_exit = True
        await self.server.shutdown()
