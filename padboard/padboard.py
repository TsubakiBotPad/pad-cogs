import aiohttp
import cv2
import discord
import numpy as np
from tsutils.formatting import extract_image_url
from tsutils.user_interaction import send_cancellation_message

from .padvision import NeuralClassifierBoardExtractor
from io import BytesIO
from collections import defaultdict
from collections import deque
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import inline


DAWNGLARE_BOARD_TEMPLATE = "https://pad.dawnglare.com/?patt={}"
CNINJA_BOARD_TEMPLATE = "https://candyninja001.github.io/Puzzled/?patt={}"


class PadBoard(commands.Cog):
    """Dawnglare Utilities"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=94080420)
        self.config.register_global(tflite_path="")

        self.logs = defaultdict(lambda: deque(maxlen=1))

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    @commands.Cog.listener("on_message")
    async def log_message(self, message):
        url = extract_image_url(message)
        if url:
            self.logs[message.author.id].append(url)

    @commands.group()
    @checks.is_owner()
    async def padboard(self, ctx):
        """PAD board utilities."""

    @padboard.command()
    async def set_tflite_path(self, ctx, *, path):
        await self.config.tflite_path.set(path)
        await ctx.tick()

    def find_image(self, user_id):
        urls = list(self.logs[user_id])
        if urls:
            return urls[-1]
        return None

    async def download_image(self, image_url):
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as r:
                if r.status == 200:
                    image_data = await r.read()
                    return image_data
        return None

    @commands.command()
    async def dawnglare(self, ctx, user: discord.Member = None):
        """Converts your most recent image to a dawnglare link

        Scans your recent messages for images (links with embeds, or uploads)
        and attempts to detect a board, and the orbs in that board. Posts a
        link to dawnglare with the contents of your board.
        """
        image_data = await self.get_recent_image(ctx, user, ctx.message)
        if not image_data:
            return

        try:
            img_board_nc = await self.nc_classify(image_data)
        except IOError:
            await send_cancellation_message(ctx, "PadVision not loaded.")
            return

        if not img_board_nc:
            await send_cancellation_message(ctx, "TFLite path not set.")
            return

        board_text_nc = ''.join([''.join(r) for r in img_board_nc])
        # Convert O (used by padvision code) to X (used by Puzzled for bombs)
        board_text_nc = board_text_nc.replace('o', 'x')
        msg = DAWNGLARE_BOARD_TEMPLATE.format(board_text_nc)
        msg += '\n' + CNINJA_BOARD_TEMPLATE.format(board_text_nc)

        await ctx.send(msg)

    async def get_recent_image(self, ctx, user: discord.Member = None, message: discord.Message = None):
        user_id = user.id if user else ctx.author.id

        image_url = extract_image_url(message)
        if image_url is None:
            image_url = self.find_image(user_id)

        if not image_url:
            if user:
                await send_cancellation_message(ctx, "Couldn't find an image in that user's recent messages.")
            else:
                await send_cancellation_message(ctx,
                    "Couldn't find an image in your recent messages. Upload or link to one and try again")
            return None

        image_data = await self.download_image(image_url)
        if not image_data:
            await send_cancellation_message("Failed to download")
            return None

        return image_data

    async def nc_classify(self, image_data):
        # TODO: Test this (for TR to do)
        nparr = np.frombuffer(image_data, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        model_path = await self.config.tflite_path()
        if not model_path:
            return None
        img_extractor = NeuralClassifierBoardExtractor(model_path, img_np, image_data)
        return img_extractor.get_board()
