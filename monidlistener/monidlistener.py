import asyncio
import os
import re
import urllib.parse
from io import BytesIO

from redbot.core import checks, commands, Config

import discord
import tsutils


class MonIdListener(commands.Cog):
    """Monster Name from ID"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=10100779)
        self.config.register_channel(enabled=False)
        
    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    @commands.Cog.listener('on_message')
    async def on_message(self, message):
        channel = message.channel
        content = message.content
        if await self.config.channel(channel).enabled():
            if message.guild is None:  # dms
                return
            if message.author == self.bot.user:  # dont reply to self
                return
            if await self.is_command(message):  # skip commands
                return
            dgcog = self.bot.get_cog("Dadguide")
            if dgcog is None:
                await channel.send("Error: Dadguide Cog not loaded.  Please alert a bot owner.")
                return
            if re.search(r'\b\d\d\d[ -,]?\d\d\d[ -,]?\d\d\d\b', content):  # friend code
                return
            if "+" in content or "plus" in content:
                return
            if re.search(r'\b\d{3,4}\b', content):
                matches = re.findall(r'\b\d{3,4}\b', content)
                ret = ""
                for i in matches:
                    m = await dgcog.find_monster(i, message.author.id)
                    if not m:  # monster not found
                        continue
                    ret += "[{}] {}\n".format(i, m.name_en)
                if ret != "":
                    await channel.send(ret)

    @commands.group(aliases=['monidlistener'])
    async def midlistener(self, ctx):
        """Commands pertaining to monster id lookup"""

    @midlistener.command()
    @checks.admin_or_permissions(manage_messages=True)
    async def enable(self, ctx):
        """Enable monster ID listener in this channel"""
        await self.config.channel(ctx.channel).enabled.set(True)
        await ctx.send("Enabled monster ID listener in this channel.")

    @midlistener.command()
    @checks.admin_or_permissions(manage_messages=True)
    async def disable(self, ctx):
        """Disable monster ID listener in this channel"""
        await self.config.channel(ctx.channel).enabled.set(False)
        await ctx.send("Disabled monster ID listener in this channel.")

    async def is_command(self, msg):
        prefixes = await self.bot.get_valid_prefixes()
        for p in prefixes:
            if msg.content.startswith(p):
                return True
        return False
