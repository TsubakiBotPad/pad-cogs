import os
from collections import defaultdict
from collections import deque

import aiohttp
import cv2
import numpy as np
from redbot.core import checks
from redbot.core import commands
from redbot.core.utils.chat_formatting import *

from padvision import padvision
from rpadutils import rpadutils

DATA_DIR = os.path.join('data', 'padboard')

DAWNGLARE_BOARD_TEMPLATE = "https://candyninja001.github.io/Puzzled/?patt={}"
MIRUGLARE_BOARD_TEMPLATE = "https://storage.googleapis.com/mirubot/websites/padsim/index.html?patt={}"


class PadBoard(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.logs = defaultdict(lambda: deque(maxlen=1))

    @commands.Cog.listener("on_message")
    async def log_message(self, message):
        url = rpadutils.extract_image_url(message)
        if url:
            self.logs[message.author.id].append(url)

    @commands.group()
    @checks.is_owner()
    async def padboard(self, ctx):
        """PAD board utilities."""

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

        img_board_nc = self.nc_classify(image_data)

        board_text_nc = ''.join([''.join(r) for r in img_board_nc])
        # Convert O (used by padvision code) to X (used by Puzzled for bombs)
        board_text_nc = board_text_nc.replace('o', 'x')
        img_url = DAWNGLARE_BOARD_TEMPLATE.format(board_text_nc)
        img_url2 = MIRUGLARE_BOARD_TEMPLATE.format(board_text_nc)

        msg = '{}\n{}'.format(img_url, img_url2)

        await ctx.send(msg)

    async def get_recent_image(self, ctx, user: discord.Member = None, message: discord.Message = None):
        user_id = user.id if user else ctx.author.id

        image_url = rpadutils.extract_image_url(message)
        if image_url is None:
            image_url = self.find_image(user_id)

        if not image_url:
            if user:
                await ctx.send(inline("Couldn't find an image in that user's recent messages."))
            else:
                await ctx.send(
                    inline("Couldn't find an image in your recent messages. Upload or link to one and try again"))
            return None

        image_data = await self.download_image(image_url)
        if not image_data:
            await ctx.send(inline("failed to download"))
            return None

        return image_data

    def nc_classify(self, image_data):
        # TODO: Test this (for TR to do)
        nparr = np.fromstring(image_data, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        model_path = '/home/tactical0retreat/git/pad-models/ICN3582626462823189160/model.tflite'
        img_extractor = padvision.NeuralClassifierBoardExtractor(model_path, img_np, image_data)
        return img_extractor.get_board()
