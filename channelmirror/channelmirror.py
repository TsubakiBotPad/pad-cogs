import logging
import re
import time
from datetime import datetime
from io import BytesIO
from typing import Optional

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

frMESSAGE_LINK = r'(https://discordapp\.com/channels/{0.guild.id}/{0.id}/(\d+)/?)'
MESSAGE_LINK = 'https://discordapp.com/channels/{0.guild.id}/{0.channel.id}/{0.id}'


class ChannelMirror(commands.Cog):
    """Channel mirroring tools."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = ChannelMirrorSettings("channelmirror")

        self.config = Config.get_conf(self, identifier=3747737700)
        self.config.register_channel(multiedit=False, mirroredit_target=None, nodeletion=False)
        self.config.init_custom("dest_message", 1)
        self.config.register_custom("dest_message", small=False)

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
            await ctx.send(inline('Check your channel IDs, or maybe the bot is not in those servers'))
            return
        conf = await get_user_confirmation(ctx, "Set up mirror of <#{}> to mirror to <#{}>?"
                                           .format(source_channel_id, dest_channel_id))
        if not conf:
            await send_cancellation_message(ctx, "Action cancelled. No action was taken.")
            return
        self.settings.add_mirrored_channel(source_channel_id, dest_channel_id)
        await send_confirmation_message(ctx, "Okay, I set up a mirror of <#{}> to <#{}>"
                                        .format(source_channel_id, dest_channel_id))

    @channelmirror.command(aliases=['rmmirror', 'rm', 'delete'])
    @checks.is_owner()
    async def remove(self, ctx, source_channel_id: int, dest_channel_id: int):
        """Remove mirroring between two channels."""
        success = self.settings.rm_mirrored_channel(source_channel_id, dest_channel_id)
        if not success:
            await ctx.send("That isn't an existing mirror.")
            return
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
        mirrored_channels = self.settings.mirrored_channels()
        gchs = set()
        if server_id:
            guild = self.bot.get_guild(server_id)
            if guild is None:
                await ctx.send("Invalid server id.")
                return
            gchs = {c.id for c in self.bot.get_guild(server_id).channels}
        msg = 'Mirrored channels\n'
        for mc_id, config in mirrored_channels.items():
            if server_id is not None and mc_id not in gchs and not gchs.intersection(config['channels']):
                continue
            channel = self.bot.get_channel(mc_id)
            channel_name = f"{channel.guild.name}/{channel.name}" if channel else 'unknown'
            multiedit = await self.config.channel_from_id(mc_id).multiedit()
            msg += '\n\n{}{} ({})'.format(mc_id, '*' if multiedit else '', channel_name)
            for channel_id in config['channels']:
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
        mirrored_channels = self.settings.mirrored_channels()
        gchs = set()
        if server_id:
            guild = self.bot.get_guild(server_id)
            if guild is None:
                await ctx.send("Invalid server id.")
                return
            gchs = {c.id for c in self.bot.get_guild(server_id).channels}
        msg = 'From:'
        for mc_id, config in mirrored_channels.items():
            if mc_id not in gchs:
                continue
            channel = self.bot.get_channel(mc_id)
            channel_name = f"{channel.guild.name}/{channel.name}" if channel else 'unknown'
            multiedit = await self.config.channel_from_id(mc_id).multiedit()
            msg += '\n{}{} ({})'.format(mc_id, '*' if multiedit else '', channel_name)
            for channel_id in config['channels']:
                channel = self.bot.get_channel(channel_id)
                channel_name = f"{channel.guild.name}/{channel.name}" if channel else 'unknown'
                msg += '\n\t{} ({})'.format(channel_id, channel_name)
        for page in pagify(msg):
            await ctx.send(box(page))

        msg = 'To:'
        for mc_id, config in mirrored_channels.items():
            if not gchs.intersection(config['channels']):
                continue
            channel = self.bot.get_channel(mc_id)
            channel_name = f"{channel.guild.name}/{channel.name}" if channel else 'unknown'
            multiedit = await self.config.channel_from_id(mc_id).multiedit()
            msg += '\n{}{} ({})'.format(mc_id, '*' if multiedit else '', channel_name)
            for channel_id in config['channels']:
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
        mirrored_messages = self.settings.get_mirrored_messages(message.channel.id, message.id)
        if not mirrored_messages:
            await ctx.send("This message isn't mirrored!")
        reacts = {}
        for react in message.reactions:
            reacts[str(react)] = react.count - 1
            for (chid, mid) in mirrored_messages:
                dest_channel = self.bot.get_channel(chid)
                if not dest_channel:
                    logger.warning('could not locate channel {}'.format(chid))
                    continue
                dest_message = await dest_channel.fetch_message(mid)
                if not dest_message:
                    logger.warning('could not locate message {}'.format(mid))
                    continue
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

    @commands.Cog.listener('on_message_without_command')
    async def mirror_msg(self, message):
        author = message.author

        if author.bot:
            return

        if (await self.bot.get_context(message)).prefix is not None:
            return

        channel = message.channel
        mirrored_channels = self.settings.get_mirrored_channels(channel.id)

        if not mirrored_channels:
            return

        last_spoke, last_spoke_timestamp = self.settings.get_last_spoke(channel.id)
        now_time = datetime.utcnow()
        last_spoke_time = datetime.utcfromtimestamp(
            last_spoke_timestamp) if last_spoke_timestamp else now_time
        attribution_required = last_spoke != author.id
        attribution_required |= (now_time - last_spoke_time).total_seconds() > ATTRIBUTION_TIME_SECONDS
        attribution_required &= not await self.config.channel(message.channel).multiedit()

        self.settings.set_last_spoke(channel.id, author.id)

        attachment_bytes = None
        filename = None

        if message.attachments:
            # If we know we're copying a message and that message has an attachment,
            # pre download it and reuse it for every upload.
            attachment_bytes = [(BytesIO(await attachment.read()), attachment.filename)
                                for attachment in message.attachments
                                if hasattr(attachment, 'url') and hasattr(attachment, 'filename')]

        if await self.config.channel(message.channel).multiedit():
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

        for dest_channel_id in mirrored_channels:
            dest_channel = self.bot.get_channel(dest_channel_id)
            if not dest_channel:
                continue
            try:
                fmessage = await self.mformat(message.content, message.channel, dest_channel)

                small = False
                if attribution_required:
                    msg = self.makeheader(message, author)
                    if len(fmessage) > 1000:
                        await dest_channel.send(msg)
                    else:
                        fmessage = msg + '\n' + fmessage
                        small = True

                if attachment_bytes:
                    try:
                        [b.seek(0) for b, fn in attachment_bytes]
                        dest_message = await dest_channel.send(
                            files=[discord.File(b, fn) for b, fn in attachment_bytes],
                            content=fmessage)
                    except discord.HTTPException:
                        try:
                            [b.seek(0) for b, fn in attachment_bytes]
                            dest_message = await dest_channel.send(file=discord.File(*attachment_bytes[0]),
                                                                   content=fmessage)
                            for b, fn in attachment_bytes[1:]:
                                await dest_channel.send(file=discord.File(b, fn))
                        except discord.HTTPException:
                            dest_message = await dest_channel.send(fmessage)
                            await dest_channel.send("<File too large to attach>")
                elif message.content:
                    dest_message = await dest_channel.send(fmessage)
                else:
                    logger.warning('Failed to mirror message from {} no action to take'.format(channel.id))
                    continue

                self.settings.add_mirrored_message(channel.id, message.id, dest_channel.id, dest_message.id)
                await self.config.custom("dest_message", dest_message.id).small.set(small)
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

        if attachment_bytes:
            [b.close() for b, fn in attachment_bytes]

    @commands.Cog.listener('on_raw_message_edit')
    async def mirror_msg_edit(self, payload):
        if not self.settings.get_mirrored_messages(payload.channel_id, payload.message_id):
            return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if 'content' in payload.data:
            await self.mirror_msg_mod(message, new_message_content=payload.data['content'])

    @commands.Cog.listener('on_raw_message_delete')
    async def mirror_msg_delete(self, payload):
        if not self.settings.get_mirrored_messages(payload.channel_id, payload.message_id):
            return
        if not await self.config.channel(self.bot.get_channel(payload.channel_id)).nodeletion():
            fmessage = DummyObject(id=payload.message_id, channel=self.bot.get_channel(payload.channel_id))
            await self.mirror_msg_mod(fmessage, delete_message_content=True)

    @commands.Cog.listener('on_raw_reaction_add')
    async def mirror_reaction_add(self, payload):
        if not self.settings.get_mirrored_messages(payload.channel_id, payload.message_id):
            return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if message.author.id != payload.user_id and not await self.config.channel(message.channel).multiedit():
            return
        await self.mirror_msg_mod(message, new_message_reaction=payload.emoji)

    @commands.Cog.listener('on_raw_reaction_remove')
    async def mirror_reaction_remove(self, payload):
        if not self.settings.get_mirrored_messages(payload.channel_id, payload.message_id):
            return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if message.author.id != payload.user_id and not await self.config.channel(message.channel).multiedit():
            return
        await self.mirror_msg_mod(message, delete_message_reaction=payload.emoji)

    async def mirror_msg_mod(self, message,
                             new_message_content: str = None,
                             delete_message_content: bool = False,
                             new_message_reaction=None,
                             delete_message_reaction=None):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return

        channel = message.channel
        mirrored_messages = self.settings.get_mirrored_messages(channel.id, message.id)
        for (dest_channel_id, dest_message_id) in mirrored_messages:
            try:
                dest_channel = self.bot.get_channel(dest_channel_id)
                if not dest_channel:
                    logger.warning('could not locate channel to mod')
                    continue
                dest_message = await dest_channel.fetch_message(dest_message_id)
                if not dest_message:
                    logger.warning('could not locate message to mod')
                    continue

                if new_message_content:
                    fcontent = await self.mformat(new_message_content, channel, dest_message.channel)
                    if await self.config.custom("dest_message", dest_message.id).small():
                        fcontent = self.makeheader(message) + '\n' + fcontent
                    if len(fcontent) > 4000:
                        fcontent = fcontent[:3971] + "... *(Continued in original)*"
                    await dest_message.edit(content=fcontent)
                elif new_message_reaction:
                    try:
                        await dest_message.add_reaction(new_message_reaction)
                    except discord.HTTPException:
                        pass
                elif delete_message_content:
                    await dest_message.delete()
                elif delete_message_reaction:
                    try:
                        await dest_message.remove_reaction(delete_message_reaction, dest_message.guild.me)
                    except discord.HTTPException:
                        pass
            except Exception as ex:
                logger.exception('Failed to mirror message edit from {} to {}:'.format(channel.id, dest_channel_id))

    def makeheader(self, message, author=None):
        return 'Posted by **{}** in *{} - #{}*:\n{}'.format(message.author.name if author is None else author.name,
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
            mirrored_messages = self.settings.get_mirrored_messages(from_link.channel.id, from_link.id)
            to_link_id = [dmid for dcid, dmid in mirrored_messages if dcid == dest_channel.id]
            if not to_link_id:
                logger.warning('could not locate link to mod')
                continue
            to_link_id = to_link_id[0]
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

    def servers(self):
        return self.bot_settings['servers']

    def get_server(self, server_id: int):
        servers = self.servers()
        if server_id not in servers:
            servers[server_id] = {}
        return servers[server_id]

    def max_mirrored_messages(self):
        return self.bot_settings['max_mirrored_messages']

    def mirrored_channels(self):
        # Mirrored channels looks like:
        #  <source_channel_id>: {
        #    'last_spoke: '<user_id>',
        #    'channels': [dest_channel_id_1, dest_channel_id2],
        #    'messages': {
        #      <source_msg_id>: [
        #         (dest_channel_id, dest_channel_msg],
        #      ]
        #    }
        #  }
        return self.bot_settings['mirrored_channels']

    def get_mirrored_channels(self, source_channel: str):
        return self.mirrored_channels().get(source_channel, {}).get('channels', [])

    def get_last_spoke(self, source_channel: str):
        spoke_values = self.mirrored_channels().get(source_channel, {})
        return spoke_values.get('last_spoke', None), spoke_values.get('last_spoke_timestamp', None)

    def set_last_spoke(self, source_channel: str, last_spoke: str):
        spoke_values = self.mirrored_channels().get(source_channel)
        spoke_values['last_spoke'] = last_spoke
        spoke_values['last_spoke_timestamp'] = time.time()
        self.save_settings()

    def add_mirrored_channel(self, source_channel: int, dest_channel: int):
        channels = self.mirrored_channels()
        if source_channel == dest_channel:
            raise commands.UserFeedbackCheckFailure('Cannot mirror a channel to itself')
        if dest_channel in channels:
            raise commands.UserFeedbackCheckFailure('Destination channel is already a source channel')
        if source_channel not in channels:
            channels[source_channel] = {
                'channels': [],
                'messages': {},
            }
        if dest_channel in channels[source_channel]['channels']:
            raise commands.UserFeedbackCheckFailure('This mirror already exists')
        channels[source_channel]['channels'].append(dest_channel)
        self.save_settings()

    def rm_mirrored_channel(self, source_channel: int, dest_channel: int):
        channels = self.mirrored_channels()
        config = channels.get(source_channel)
        if config and dest_channel in config['channels']:
            dest_channel_config = config['channels']
            dest_channel_config.remove(dest_channel)
            if not dest_channel_config:
                channels.pop(source_channel)
            self.save_settings()
            return True
        else:
            return False

    def add_mirrored_message(self, source_channel: int, source_message: str, dest_channel: int, dest_message: str):
        channel_config = self.mirrored_channels()[source_channel]
        messages = channel_config['messages']
        if source_message not in messages:
            messages[source_message] = []

        targets = messages[source_message]
        new_entry = [dest_channel, dest_message]
        if new_entry not in targets:
            targets.append(new_entry)
            self.save_settings()

        if len(messages) > self.max_mirrored_messages():
            oldest_msg = min(messages.keys())
            messages.pop(oldest_msg)
            self.save_settings()

    def get_mirrored_messages(self, source_channel: int, source_message: str):
        """Returns [(channel_id, message_id), ...]"""
        channel_config = self.mirrored_channels().get(source_channel, {})
        return channel_config.get('messages', {}).get(source_message, [])
