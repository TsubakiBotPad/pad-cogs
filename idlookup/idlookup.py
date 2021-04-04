import asyncio
import logging
import os
import random
import re
import urllib.parse

from copy import deepcopy
from io import BytesIO
from typing import TYPE_CHECKING, List

from redbot.core import checks, commands, data_manager, Config
from redbot.core.utils.chat_formatting import box, escape, pagify

import discord
import tsutils

from padinfo.menu.id import IdMenu, IdMenuPanes
from padinfo.view.id_traceback import IdTracebackView, IdTracebackViewProps
from padinfo.menu.monster_list import MonsterListMenu, MonsterListMenuPanes, MonsterListEmoji

try:
    import re2 as re
except ImportError:
    try:
        import regex as re
    except ImportError:
        import re

class Idlookup(commands.Cog):
    """Monster Name from ID"""
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=717432306)

    @commands.Cog.listener('on_message')
    async def on_message(self, message):
        channel = message.channel
        content = message.content
        if await self.config.channel(channel).enabled():
            if message.guild is None: #dms
                return
            if author == self.bot.user: #dont reply to self
                return
            if await self.is_command(message): #skip commands
                return
            dgcog = self.bot.get_cog("Dadguide")
            if dgcog is None:
                await channel.send(inline("Error: Dadguide Cog not loaded.  Please alert a bot owner."))
                return
            if re.search(r'\b\d\d\d[ -]?\d\d\d[ -]?\d\d\d\b', content): #friend code
                return
            if re.search(r'\d{3,4}', content):
                matches = re.findall(r'\d{3,4}',content)
                ret = ""
                for i in matches:
                    m = await dgcog.find_monster(i, author.id)
                    if not m: #monster not found
                        continue
                    ret+="[{}] {}\n".format(i, m.name_en)
                await channel.send(ret)
                return
        else:
            return

    @commands.command()
    @checks.admin_or_permissions(administrator=True)
    async def idlenable(self, ctx, *channels: discord.TextChannel):
        """Enable idlookup in channel"""
        self.config.register_channel(enabled=True)
        await ctx.send("Enabled idlookup in this channel")

    @commands.command()
    @checks.admin_or_permissions(administrator=True)
    async def idldisable(self, ctx, *channels: discord.TextChannel):
        """Disable idlookup from chosen channel(s)"""
        self.config.register_channel(enabled=False)
        await ctx.send("Disabled idlookup in this channel")

    async def is_command(self, msg):
        prefixes = await self.bot.get_prefix(msg)
        if not isinstance(prefixes, list):
            prefixes = [prefixes]
        for p in prefixes:
            if msg.content.startswith(p):
                return True
        return False
