import asyncio
import datetime
import re

import discord
from redbot.core.bot import Red

from redbot.core import checks, modlog
from redbot.core import commands
from redbot.core.utils.chat_formatting import inline, box, pagify


class MsgUtils(commands.Cog):
    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    @commands.command()
    @checks.mod_or_permissions(manage_guild=True)
    async def editmsg(self, ctx, channel: discord.TextChannel, msg_id: int, *, new_msg: str):
        """Given a channel and an ID for a message printed in that channel, replaces it.

        To find a message ID, enable developer mode in Discord settings and
        click the ... on a message.
        """
        try:
            msg = await channel.fetch_message(msg_id)
        except discord.NotFound:
            await ctx.send(inline('Cannot find that message, check the channel and message id'))
            return
        except discord.Forbidden:
            await ctx.send(inline('No permissions to do that'))
            return
        if msg.author.id != self.bot.user.id:
            await ctx.send(inline('Can only edit messages I own'))
            return

        await msg.edit(content=new_msg)
        await ctx.send(inline('done'))

    @commands.command()
    @checks.mod_or_permissions(manage_guild=True)
    async def dumpchannel(self, ctx, channel: discord.TextChannel, msg_id: int = None):
        """Given a channel and an ID for a message printed in that channel, dumps it
        boxed with formatting escaped and some issues cleaned up.

        To find a message ID, enable developer mode in Discord settings and
        click the ... on a message.
        """
        await self._dump(ctx, channel, msg_id)

    @commands.command()
    async def dumpmsg(self, ctx, msg_id: int = None):
        """Given an ID for a message printed in the current channel, dumps it
        boxed with formatting escaped and some issues cleaned up.

        To find a message ID, enable developer mode in Discord settings and
        click the ... on a message.
        """
        await self._dump(ctx, ctx.channel, msg_id)

    async def _dump(self, ctx, channel: discord.TextChannel = None, msg_id: int = None):
        if msg_id:
            msg = await channel.fetch_message(msg_id)
        else:
            msg_limit = 2 if channel == ctx.channel else 1
            async for message in channel.history(limit=msg_limit):
                msg = message
        content = msg.content.strip()
        content = re.sub(r'<(:[0-9a-z_]+:)\d{18}>', r'\1', content, flags=re.IGNORECASE)
        content = box(content.replace('`', u'\u200b`'))
        await ctx.send(content)

    @commands.command()
    async def dumpmsgexact(self, ctx, msg_id: int):
        """Given an ID for a message printed in the current channel, dumps it
        boxed with formatting escaped.

        To find a message ID, enable developer mode in Discord settings and
        click the ... on a message.
        """
        msg = await ctx.channel.fetch_message(msg_id)
        content = msg.content.strip()
        content = box(content.replace('`', u'\u200b`'))
        await ctx.send(content)
