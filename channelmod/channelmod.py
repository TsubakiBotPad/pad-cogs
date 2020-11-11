import aiohttp
import discord
import logging
import re
import time
import traceback
from typing import Optional
from datetime import datetime
from io import BytesIO
from redbot.core import checks, commands, Config
from redbot.core.utils.chat_formatting import inline, pagify, box
from tsutils import CogSettings, auth_check, replace_emoji_names_with_code, fix_emojis_for_server

logger = logging.getLogger('red.misc-cogs.channelmod')

# Three hour cooldown
ATTRIBUTION_TIME_SECONDS = 60 * 60 * 3

frMESSAGE_LINK = r'(https://discordapp\.com/channels/{0.guild.id}/{0.id}/(\d+)/?)'
MESSAGE_LINK = 'https://discordapp.com/channels/{0.guild.id}/{0.channel.id}/{0.id}'


class ChannelMod(commands.Cog):
    """Channel moderation tools."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = ChannelModSettings("channelmod")
        self.channel_last_spoke = {}

        self.config = Config.get_conf(self, identifier=3747737700)
        self.config.register_channel(multiedit=False)

        GACOG = self.bot.get_cog("GlobalAdmin")
        if GACOG: self.bot.get_cog("GlobalAdmin").register_perm("channelmod")

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    @commands.group()
    async def channelmod(self, ctx):
        """Manage channel moderation settings"""

    @channelmod.command()
    @checks.is_owner()
    async def addmirror(self, ctx, source_channel_id: int, dest_channel_id: int, docheck: bool = True):
        """Set mirroring between two channels."""
        if docheck and (not self.bot.get_channel(source_channel_id) or not self.bot.get_channel(dest_channel_id)):
            await ctx.send(inline('Check your channel IDs, or maybe the bot is not in those servers'))
            return
        self.settings.add_mirrored_channel(source_channel_id, dest_channel_id)
        await ctx.tick()

    @channelmod.command()
    @checks.is_owner()
    async def rmmirror(self, ctx, source_channel_id: int, dest_channel_id: int):
        """Remove mirroring between two channels."""
        success = self.settings.rm_mirrored_channel(source_channel_id, dest_channel_id)
        if not success:
            await ctx.send("That isn't an existing mirror.")
            return
        await ctx.tick()

    @channelmod.command()
    @checks.is_owner()
    async def multiedit(self, ctx, channel: Optional[discord.TextChannel], enable: bool):
        """Opt in a channel to multi-edit mode."""
        if channel is None:
            channel = ctx.channel
        await self.config.channel(channel).multiedit.set(multiedit)
        await ctx.tick()

    @channelmod.command()
    @checks.is_owner()
    async def mirrorconfig(self, ctx, server_id: int = None):
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
            multiedit = await self.config.channel(discord.Object(id=mc_id)).multiedit()
            msg += '\n\n{}{} ({})'.format(mc_id, '*' if multiedit else '', channel_name)
            for channel_id in config['channels']:
                if server_id is not None and mc_id not in gchs and not channel_id not in gchs:
                    continue
                channel = self.bot.get_channel(channel_id)
                channel_name = f"{channel.guild.name}/{channel.name}" if channel else 'unknown'
                msg += '\n\t{} ({})'.format(channel_id, channel_name)
        msg += '\n\n* indicates multi-edit'
        await ctx.send(box(msg))


    @channelmod.command()
    @checks.is_owner()
    async def guildmirrorconfig(self, ctx, server_id: int):
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
            multiedit = await self.config.channel(discord.Object(id=mc_id)).multiedit()
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
            multiedit = await self.config.channel(discord.Object(id=mc_id)).multiedit()
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


    @channelmod.command()
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
        for r, c in reacts.items():
            o += "{{}}: {{:{}}}\n".format(maxlen).format(r, c)
        await ctx.send(o)

    @channelmod.command()
    @auth_check('channelmod')
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

        if (await bot.get_context(message)).prefix is not None:
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
        self.settings.set_last_spoke(channel.id, author.id)

        attachment_bytes = None
        filename = None

        if await self.config.channel(message.channel).multiedit():
            await message.delete()
            idmess = await message.channel.send("Pending...")
            message = await message.channel.send(message.content, files=[await a.to_file() for a in message.attachments])
            await idmess.edit(content=str(message.id))

        if message.attachments:
            # If we know we're copying a message and that message has an attachment,
            # pre download it and reuse it for every upload.
            attachment = message.attachments[0]
            if hasattr(attachment, 'url') and hasattr(attachment, 'filename'):
                url = attachment.url
                filename = attachment.filename
                attachment_bytes = BytesIO(await attachment.read())

        for dest_channel_id in mirrored_channels:
            dest_channel = self.bot.get_channel(dest_channel_id)
            if not dest_channel:
                continue
            try:
                if attribution_required:
                    msg = self.makeheader(message)
                    await dest_channel.send(msg)

                fmessage = await self.mformat(message.content, message.channel, dest_channel)

                if attachment_bytes and filename:
                    attachment_bytes.seek(0)
                    dest_message = await dest_channel.send(file=discord.File(attachment_bytes, filename),
                                                           content=fmessage)
                elif message.content:
                    dest_message = await dest_channel.send(fmessage)
                else:
                    logger.warning('Failed to mirror message from {} no action to take'.format(channel.id))
                    continue

                self.settings.add_mirrored_message(
                    channel.id, message.id, dest_channel.id, dest_message.id)
            except Exception as ex:
                if dest_channel.guild.owner:
                    try:
                        message = ("Hi, {1.guild.owner}!  This is an automated message from the Tsubaki team to let"
                                   " you know that your server, {1.guild.name}, has been configured to mirror"
                                   " messages from {0.name} (from {0.guild.name}) to {1.name}, but your channel"
                                   " doesn't give me manage message permissions!  Please do make sure to allow"
                                   " me permissions to send messages, embed links, and attach files!  It's also"
                                   " okay to turn off message mirroring from your channel.  If you need help, contact"
                                   " us via `{2}feedback`!"
                                   "").format(channel, dest_channel, (await self.bot.get_valid_prefixes())[0])
                        await dest_channel.guild.owner.send(message)
                    except Exception:
                        logger.exception("Owner message failed.")
                logger.exception(
                    'Failed to mirror message from {} to {}: {}'.format(channel.id, dest_channel_id, str(ex)))

        if attachment_bytes:
            attachment_bytes.close()

    @commands.Cog.listener('on_message_edit')
    async def mirror_msg_edit(self, before, after):
        if before.content != after.content:
            await self.mirror_msg_mod(before, new_message_content=after.content)

    @commands.Cog.listener('on_message_delete')
    async def mirror_msg_delete(self, message):
        await self.mirror_msg_mod(message, delete_message_content=True)

    @commands.Cog.listener('on_reaction_add')
    async def mirror_reaction_add(self, reaction, user):
        message = reaction.message
        if message.author.id != user.id and not await self.config.channel(message.channel).multiedit():
            return
        await self.mirror_msg_mod(message, new_message_reaction=reaction.emoji)

    @commands.Cog.listener('on_reaction_remove')
    async def mirror_reaction_remove(self, reaction, user):
        message = reaction.message
        if message.author.id != user.id and not await self.config.channel(message.channel).multiedit():
            return
        await self.mirror_msg_mod(message, delete_message_reaction=reaction.emoji)

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

    def makeheader(self, message):
        return 'Posted by **{}** in *{} - #{}*:\n{}'.format(message.author.name,
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
        # text = self.emojify(text)
        return text

    def emojify(self, message):
        emojis = list()
        for guild in self.bot.guilds:
            emojis.extend(guild.emojis)
        message = replace_emoji_names_with_code(emojis, message)
        return fix_emojis_for_server(emojis, message)


class ChannelModSettings(CogSettings):
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
