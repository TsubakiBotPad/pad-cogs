import logging
import re
import time
from io import BytesIO
from typing import List, Optional

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box, inline, pagify
from tsutils.cog_settings import CogSettings
from tsutils.cogs.globaladmin import auth_check
from tsutils.emoji import fix_emojis_for_server, replace_emoji_names_with_code
from tsutils.helper_classes import DummyObject
from tsutils.user_interaction import get_user_confirmation, send_cancellation_message, send_confirmation_message, \
    send_repeated_consecutive_messages

logger = logging.getLogger('red.misc-cogs.channelmirror')

# Three hour cooldown
ATTRIBUTION_TIME_SECONDS = 60 * 60 * 3
MAX_MIRRORED_MESSAGES = 100

frMESSAGE_LINK = r'(https://discord\.com/channels/{0.guild.id}/{0.id}/(\d+)/?)'
MESSAGE_LINK = 'https://discord.com/channels/{0.guild.id}/{0.channel.id}/{0.id}'


class ChannelMirror(commands.Cog):
    """Channel mirroring tools."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = ChannelMirrorSettings("channelmirror")

        self.config = Config.get_conf(self, identifier=3747737700)
        self.config.register_channel(last_spoke=0, last_spoke_timestamp=0, mirrored_channels=[], mirrored_messages={},
                                     multiedit=False, mirroredit_target=None, nodeletion=False)
        self.config.init_custom("message", 1)
        self.config.register_custom("message", attribute=False)

        GACOG = self.bot.get_cog("GlobalAdmin")
        if GACOG:
            GACOG.register_perm("channelmirror")

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    @commands.group(aliases=['channelmod'])
    async def channelmirror(self, ctx):
        """Manage channel mirroring settings"""

    @channelmirror.command(aliases=['addmirror'])
    @checks.is_owner()
    async def add(self, ctx, source_channel_id: int, dest_channel_id: int, docheck: bool = True):
        """Set mirroring between two channels."""
        if docheck and (not self.bot.get_channel(source_channel_id) or not self.bot.get_channel(dest_channel_id)):
            await ctx.send('Check your channel IDs, or maybe the bot is not in those servers')
            return
        if not await get_user_confirmation(ctx, f"Set <#{dest_channel_id}> to mirror message from "
                                                f"<#{source_channel_id}>?"):
            await send_cancellation_message(ctx, "Action cancelled. No action was taken.")
            return
        async with self.config.channel_from_id(source_channel_id).mirrored_channels() as mirrored_channels:
            if dest_channel_id not in mirrored_channels:
                mirrored_channels.append(dest_channel_id)
        await send_confirmation_message(ctx, f"Mirror from <#{source_channel_id}> to <#{dest_channel_id}> successful")

    @channelmirror.command(aliases=['rmmirror', 'rm', 'delete'])
    @checks.is_owner()
    async def remove(self, ctx, source_channel_id: int, dest_channel_id: int):
        """Remove mirroring between two channels."""
        async with self.config.channel_from_id(source_channel_id).mirrored_channels() as mirrored_channels:
            if dest_channel_id in mirrored_channels:
                mirrored_channels.remove(dest_channel_id)
            else:
                return await ctx.send("That isn't an existing mirror.")
        await ctx.tick()

    @channelmirror.command()
    @checks.is_owner()
    async def multiedit(self, ctx, channel: Optional[discord.TextChannel], enable: bool = True):
        """Opt in a channel to multi-edit mode."""
        if channel is None:
            channel = ctx.channel
        await self.config.channel(channel).multiedit.set(enable)
        await ctx.tick()

    @channelmirror.command()
    @checks.is_owner()
    async def nodeletion(self, ctx, channel: Optional[discord.TextChannel], enable: bool = True):
        """Opt in a channel to no-deletion mode."""
        if channel is None:
            channel = ctx.channel
        await self.config.channel(channel).nodeletion.set(enable)
        await ctx.tick()

    @channelmirror.command(aliases=['mirrorconfig'])
    @checks.is_owner()
    async def config(self, ctx, server_id: int = None):
        """List mirror config."""
        gchs = set()
        if server_id:
            guild = self.bot.get_guild(server_id)
            if guild is None:
                await ctx.send("Invalid server id.")
                return
            gchs = {c.id for c in self.bot.get_guild(server_id).channels}
        msg = 'Mirrored channels\n'
        for mc_id, config in (await self.config.all_channels()).items():
            if server_id is not None and mc_id not in gchs and not gchs.intersection(config['mirrored_channels']):
                continue
            channel = self.bot.get_channel(mc_id)
            channel_name = f"{channel.guild.name}/{channel.name}" if channel else 'unknown'
            multiedit = await self.config.channel_from_id(mc_id).multiedit()
            msg += '\n\n{}{} ({})'.format(mc_id, '*' if multiedit else '', channel_name)
            for channel_id in config['mirrored_channels']:
                if server_id is not None and mc_id not in gchs and not channel_id not in gchs:
                    continue
                channel = self.bot.get_channel(channel_id)
                channel_name = f"{channel.guild.name}/{channel.name}" if channel else 'unknown'
                msg += '\n\t{} ({})'.format(channel_id, channel_name)
        msg += '\n\n* indicates multi-edit'
        for page in pagify(msg):
            await ctx.send(box(page))

    @channelmirror.command(aliases=['guildmirrorconfig'])
    @checks.is_owner()
    async def guildconfig(self, ctx, server_id: int):
        """List mirror config for a guild."""
        gchs = set()
        if server_id:
            guild = self.bot.get_guild(server_id)
            if guild is None:
                await ctx.send("Invalid server id.")
                return
            gchs = {c.id for c in self.bot.get_guild(server_id).channels}

        msg = 'From:'
        for mc_id, config in (await self.config.all_channels()).items():
            if mc_id not in gchs:
                continue
            channel = self.bot.get_channel(mc_id)
            channel_name = f"{channel.guild.name}/{channel.name}" if channel else 'unknown'
            multiedit = await self.config.channel_from_id(mc_id).multiedit()
            msg += '\n{}{} ({})'.format(mc_id, '*' if multiedit else '', channel_name)
            for channel_id in config['mirrored_channels']:
                channel = self.bot.get_channel(channel_id)
                channel_name = f"{channel.guild.name}/{channel.name}" if channel else 'unknown'
                msg += '\n\t{} ({})'.format(channel_id, channel_name)
        for page in pagify(msg):
            await ctx.send(box(page))

        msg = 'To:'
        for mc_id, config in (await self.config.all_channels()).items():
            if not gchs.intersection(config['mirrored_channels']):
                continue
            channel = self.bot.get_channel(mc_id)
            channel_name = f"{channel.guild.name}/{channel.name}" if channel else 'unknown'
            multiedit = await self.config.channel_from_id(mc_id).multiedit()
            msg += '\n{}{} ({})'.format(mc_id, '*' if multiedit else '', channel_name)
            for channel_id in config['mirrored_channels']:
                if channel_id not in gchs:
                    continue
                channel = self.bot.get_channel(channel_id)
                channel_name = channel.name if channel else 'unknown'
                msg += '\n\t{} ({})'.format(channel_id, channel_name)
        for page in pagify(msg):
            await ctx.send(box(page))

        await ctx.send(inline('* indicates multi-edit'))

    @channelmirror.command()
    async def countreactions(self, ctx, message: discord.Message):
        """Count reactions on a message and all of its mirrors.

        The message can be a link, a message id (if used in the same
        channel as the message), or the channel_id and message_id
        separated by a dash (channel_id-message-id)"""
        mirrored_messages = (await self.config.channel(message.channel).mirrored_messages())[str(message.id)]
        if not mirrored_messages:
            await ctx.send("This message isn't mirrored!")
        reacts = {}
        for react in message.reactions:
            reacts[str(react)] = react.count - 1
            for (chid, mids) in mirrored_messages:
                dest_channel = self.bot.get_channel(chid)
                if not dest_channel:
                    logger.warning('could not locate channel {}'.format(chid))
                    continue
                dest_messages = [await dest_channel.fetch_message(mid) for mid in mids]
                if not all(dest_messages):
                    logger.warning('could not locate messages {}'.format(mids))
                    continue
                for dest_message in dest_messages:
                    dest_reaction = discord.utils.find(lambda r: r == react, dest_message.reactions)
                    if not dest_reaction:
                        logger.warning('could not locate reaction {}'.format(react))
                        continue
                    reacts[str(react)] += dest_reaction.count - 1
        o = ""
        maxlen = len(str(max(reacts.values(), key=lambda x: len(str(x)))))
        for reaction, count in reacts.items():
            o += "{{}}: {{:{}}}\n".format(maxlen).format(reaction, count)
        await ctx.send(o)

    @channelmirror.command()
    @auth_check('channelmirror')
    async def catchup(self, ctx, channel, from_message, to_message=None):
        """Catch up a mirror for all messages after from_message (inclusive)"""
        if channel.isdigit():
            channel = self.bot.get_channel(int(channel))
        else:
            channel = await self.catchup.do_conversion(ctx, discord.TextChannel, channel, "channel")

        if from_message.isdigit():
            from_message = await channel.fetch_message(int(from_message))
        else:
            from_message = await self.catchup.do_conversion(ctx, discord.Message, from_message, "from_message")

        if to_message is None:
            pass
        elif to_message.isdigit():
            to_message = await channel.fetch_message(int(to_message))
        else:
            to_message = await self.catchup.do_conversion(ctx, discord.Message, to_message, "to_message")

        async with ctx.typing():
            await self.mirror_msg(from_message)
            async for message in channel.history(limit=None, after=from_message, before=to_message):
                await self.mirror_msg(message)
            if to_message:
                await self.mirror_msg(to_message)
        await ctx.tick()

    @commands.Cog.listener('on_message')
    async def mirror_msg(self, message):
        author = message.author

        if author.bot:
            return

        if (await self.bot.get_context(message)).prefix is not None:
            return

        channel = message.channel
        mirrored_channels = await self.config.channel(channel).mirrored_channels()
        multiedit = await self.config.channel(channel).multiedit()

        if not mirrored_channels:
            return

        if multiedit and len(message.content) > 2000:
            return await message.channel.send("I can't send this message as it's longer than 2000 characters.")

        last_spoke = await self.config.channel(channel).last_spoke()
        last_spoke_timestamp = await self.config.channel(channel).last_spoke_timestamp()
        attribution_required = last_spoke != author.id
        attribution_required |= time.time() - last_spoke_timestamp > ATTRIBUTION_TIME_SECONDS
        attribution_required &= not multiedit

        await self.config.custom('message', message.id).attribute.set(attribution_required)
        await self.config.channel(channel).last_spoke.set(author.id)
        await self.config.channel(channel).last_spoke_timestamp.set(time.time())

        attachment_bytes = [(BytesIO(await attachment.read()), attachment.filename)
                            for attachment in message.attachments]

        if multiedit:
            await message.delete()
            idmess = await channel.send("Pending...")
            attachments = message.attachments
            try:
                message = await channel.send(message.content,
                                             files=[await a.to_file() for a in attachments])
            except discord.HTTPException:
                try:
                    message = await channel.send(content=message.content)
                    for a in attachments:
                        await channel.send(file=await a.to_file())
                except discord.HTTPException:
                    if message.content:
                        message = await channel.send(message.content)
                    await channel.send(
                        f"<{author.mention} File too large for this channel. Other attachments not shown>")

            await idmess.edit(content=str(message.id))

        linked_messages = []

        for dest_channel_id in mirrored_channels:
            dest_channel = self.bot.get_channel(dest_channel_id)
            if not dest_channel:
                continue
            try:
                if not (attachment_bytes or message.content):
                    logger.warning('Failed to mirror message from {} no action to take'.format(channel.id))
                    continue

                message.content = await self.mformat(message.content, message.channel, dest_channel)
                fmessages = await self.split_message(message)

                [b.seek(0) for b, fn in attachment_bytes]
                try:
                    dest_messages = [await dest_channel.send(
                        files=[discord.File(b, fn) for b, fn in attachment_bytes],
                        content=fmessage) for fmessage in fmessages]
                except discord.HTTPException:
                    dest_messages = [await dest_channel.send(fmessage) for fmessage in fmessages]
                    try:
                        for b, fn in attachment_bytes:
                            await dest_channel.send(file=discord.File(b, fn))
                    except discord.HTTPException:
                        await dest_channel.send("<File too large to attach>")

                linked_messages.append((dest_channel.id, [m.id for m in dest_messages]))

            except discord.Forbidden:
                if dest_channel.guild.owner:
                    try:
                        notify = ("Hi, {1.guild.owner}!  This is an automated message from the Tsubaki team to let"
                                  " you know that your server, {1.guild.name}, has been configured to mirror"
                                  " messages from {0.name} (from {0.guild.name}) to {1.name}, but your channel"
                                  " doesn't give me manage message permissions!  Please do make sure to allow"
                                  " me permissions to send messages, embed links, and attach files!  It's also"
                                  " okay to turn off message mirroring from your channel.  If you need help, contact"
                                  " us via `{2}feedback`!"
                                  "").format(channel, dest_channel, (await self.bot.get_valid_prefixes())[0])

                        fctx = await self.bot.get_context(message)
                        fctx.send = dest_channel.guild.owner.send
                        fctx.history = dest_channel.guild.owner.history
                        await send_repeated_consecutive_messages(fctx, notify)
                    except Exception:
                        logger.exception("Owner message failed.")
            except Exception as ex:
                logger.exception(
                    'Failed to mirror message from {} to {}: {}'.format(channel.id, dest_channel_id, str(ex)))

        async with self.config.channel(channel).mirrored_messages() as mirrored_messages:
            mirrored_messages[str(message.id)] = linked_messages
            if len(mirrored_messages) > MAX_MIRRORED_MESSAGES:
                mirrored_messages.pop(min(mirrored_messages))  # This works because snowflakes sort by time
        [b.close() for b, fn in attachment_bytes]

    @commands.Cog.listener('on_raw_message_edit')
    async def mirror_msg_edit(self, payload):
        if str(payload.message_id) not in await self.config.channel_from_id(payload.channel_id).mirrored_messages():
            return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if 'content' in payload.data:
            await self.mirror_msg_mod(message, new_message_content=payload.data['content'])

    @commands.Cog.listener('on_raw_message_delete')
    async def mirror_msg_delete(self, payload):
        if str(payload.message_id) not in await self.config.channel_from_id(payload.channel_id).mirrored_messages():
            return
        if not await self.config.channel(self.bot.get_channel(payload.channel_id)).nodeletion():
            fmessage = DummyObject(id=payload.message_id, channel=self.bot.get_channel(payload.channel_id))
            await self.mirror_msg_mod(fmessage, delete_message_content=True)

    @commands.Cog.listener('on_raw_reaction_add')
    async def mirror_reaction_add(self, payload):
        if str(payload.message_id) not in await self.config.channel_from_id(payload.channel_id).mirrored_messages():
            return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if message.author.id != payload.user_id and not await self.config.channel(message.channel).multiedit():
            return
        await self.mirror_msg_mod(message, new_message_reaction=payload.emoji)

    @commands.Cog.listener('on_raw_reaction_remove')
    async def mirror_reaction_remove(self, payload):
        if str(payload.message_id) not in await self.config.channel_from_id(payload.channel_id).mirrored_messages():
            return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if message.author.id != payload.user_id and not await self.config.channel(message.channel).multiedit():
            return
        await self.mirror_msg_mod(message, delete_message_reaction=payload.emoji)

    async def split_message(self, message: discord.Message, fit_in: Optional[int] = None) -> List[str]:
        attribute = await self.config.custom('message', message.id).attribute()
        content = (self.makeheader(message) if attribute else '') + message.content
        if fit_in is None:
            return list(pagify(content, delims=['\n\n', '\n'], shorten_by=0, page_length=1750))

        messages = list(pagify(content, delims=['\n\n', '\n'], shorten_by=0, page_length=2000))
        if len(messages) > fit_in:
            messages = messages[:fit_in]
            messages[-1] = messages[-1][:1971] + "... *(Continued in original)*"
        elif len(messages) < fit_in:
            messages += ["[Placeholder - This message used to be longer!]"] * (fit_in - len(messages))
        return messages

    async def mirror_msg_mod(self, message,
                             new_message_content: str = None,
                             delete_message_content: bool = False,
                             new_message_reaction=None,
                             delete_message_reaction=None):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return

        channel = message.channel
        mirrored_messages = (await self.config.channel(channel).mirrored_messages())[str(message.id)]
        for (dest_channel_id, dest_message_ids) in mirrored_messages:
            try:
                dest_channel = self.bot.get_channel(dest_channel_id)
                if not dest_channel:
                    logger.warning('could not locate channel to mod')
                    continue
                dest_messages = [await dest_channel.fetch_message(m_id) for m_id in dest_message_ids]
                if not all(dest_messages):
                    logger.warning('could not locate message to mod')
                    continue

                if new_message_content:
                    message.content = await self.mformat(new_message_content, channel, dest_channel)
                    fcontents = await self.split_message(message, fit_in=len(dest_message_ids))
                    for dest_message, content in zip(dest_messages, fcontents):
                        await dest_message.edit(content=content)
                elif new_message_reaction:
                    try:
                        await dest_messages[-1].add_reaction(new_message_reaction)
                    except discord.HTTPException:
                        pass
                elif delete_message_content:
                    for dest_message in dest_messages:
                        await dest_message.delete()
                elif delete_message_reaction:
                    try:
                        await dest_messages[-1].remove_reaction(delete_message_reaction, dest_channel.me)
                    except discord.HTTPException:
                        pass
            except Exception as ex:
                logger.exception('Failed to mirror message edit from {} to {}:'.format(channel.id, dest_channel_id))

    def makeheader(self, message):
        return 'Posted by **{}** in *{} - #{}*:\n{}\n'.format(message.author.name,
                                                              message.guild.name,
                                                              message.channel.name,
                                                              message.jump_url)

    async def mformat(self, text, from_channel, dest_channel):
        # LINKS
        for link, mid in re.findall(frMESSAGE_LINK.format(from_channel), text):
            from_link = await from_channel.fetch_message(mid)
            if not from_link:
                logger.warning('could not locate link to copy')
                continue
            mirrored_messages = (await self.config.channel(from_channel).mirrored_messages())[str(from_link.id)]
            to_link_ids = [dmids for dcid, dmids in mirrored_messages if dcid == dest_channel.id]
            if not to_link_ids:
                logger.warning('could not locate link to mod')
                continue
            to_link_id = to_link_ids[0][0]
            dest_link = await dest_channel.fetch_message(to_link_id)

            newlink = MESSAGE_LINK.format(dest_link)
            text = text.replace(link, newlink)

        # ROLES
        for rtext, rid in re.findall(r'(<@&(\d+)>)', text):
            target = from_channel.guild.get_role(int(rid))
            if target is None:
                logger.warning('could not locate role to mod')
                continue
            dest = discord.utils.get(dest_channel.guild.roles, name=target.name)
            if dest is None:
                repl = "\\@" + target.name
            else:
                repl = "<@&{}>".format(dest.id)
            text = text.replace(rtext, repl)

        # MENTIONS
        for utext, uid in re.findall(r'(<@!(\d+)>)', text):
            target = from_channel.guild.get_member(int(uid))
            if target is None:
                logger.warning('could not locate user to mod')
                continue
            text = text.replace(utext, target.name)

        # CHANNELS
        for ctext, cid in re.findall(r'(<#(\d+)>)', text):
            target = from_channel.guild.get_channel(int(cid))
            if target is None:
                logger.warning('could not locate channel to mod')
                continue
            text = text.replace(ctext, "\\#" + target.name)

        # EVERYONE
        text = re.sub(r"@everyone\b", "@\u200beveryone", text)
        text = re.sub(r"@here\b", "@\u200bhere", text)

        # EMOJI
        text = self.emojify(text)
        return text

    def emojify(self, message):
        emojis = list()
        for guild in self.bot.guilds:
            emojis.extend(guild.emojis)
        message = replace_emoji_names_with_code(emojis, message)
        return fix_emojis_for_server(emojis, message)

    @channelmirror.command(aliases=['setmirroreditchannel'])
    @checks.is_owner()
    async def seteditchannel(self, ctx, channel: discord.TextChannel):
        """Sets the edit_target for the current channel to `channelid`"""
        await self.config.channel(ctx.channel).mirroredit_target.set(channel.id)
        await ctx.tick()

    @channelmirror.command(aliases=['rmmirroreditchannel'])
    @checks.is_owner()
    async def rmeditchannel(self, ctx):
        """Removes the mirroredit_target for the current channel"""
        await self.config.channel(ctx.channel).mirroredit_target.set(None)
        await ctx.tick()

    @commands.command(aliases=['medit'])
    @checks.mod_or_permissions(manage_messages=True)
    async def mirroredit(self, ctx, message, *, content):
        """Given a message ID from the mirroredit-configured channel, replaces it.
        This is a TEMPORARY command until the alias command is fixed to respect newlines.
        At that point, we will just use aliases instead of configuring channel IDs here.
        """
        try:
            message = await commands.MessageConverter().convert(ctx, message)
        except commands.MessageNotFound as e:
            channel_id = await self.config.channel(ctx.channel).mirroredit_target()
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                await ctx.send(
                    "Invalid mirroredit channel.  Please add one with `{0.prefix}setmirroreditchannel`".format(ctx))
                return
            try:
                message = await channel.fetch_message(int(message))
            except (discord.NotFound, ValueError):
                raise e
        if message.author != ctx.me:
            await ctx.send("I can't edit a message that's not my own")
            return
        # Even if permissions change in the target channel in between the bot sending and
        # editing the message, the bot will still be able to edit the message, so testing
        # for discord.Forbidden is not actually required here (this is in contrast to
        # human users lacking an edit button when channels are read-only but they previously)
        # had sent a message in them. Tested 2020-12-02.
        await message.edit(content=content)
        await ctx.tick()


class ChannelMirrorSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'servers': {},
            'mirrored_channels': {},
            'max_mirrored_messages': 20,
        }
        return config
