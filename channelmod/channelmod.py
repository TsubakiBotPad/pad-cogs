import io
import logging
import time
import traceback
from datetime import datetime

import aiohttp
import discord
from redbot.core import checks
from redbot.core import commands
from redbot.core.utils.chat_formatting import inline

from rpadutils import CogSettings, box

log = logging.getLogger("red.admin")

# Three hour cooldown
ATTRIBUTION_TIME_SECONDS = 60 * 60 * 3


class ChannelMod(commands.Cog):
    """Channel moderation tools."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = ChannelModSettings("channelmod")
        self.channel_last_spoke = {}

    @commands.group()
    @checks.is_owner()
    async def channelmod(self, ctx):
        """Manage channel moderation settings"""

    @channelmod.command()
    async def addmirror(self, ctx, source_channel_id: int, dest_channel_id: int, docheck: bool = True):
        """Set mirroring between two channels."""
        if docheck and (not self.bot.get_channel(source_channel_id) or not self.bot.get_channel(dest_channel_id)):
            await ctx.send(inline('Check your channel IDs, or maybe the bot is not in those servers'))
            return
        self.settings.add_mirrored_channel(source_channel_id, dest_channel_id)
        await ctx.send(inline('Done'))

    @channelmod.command()
    @checks.is_owner()
    async def rmmirror(self, ctx, source_channel_id: int, dest_channel_id: int, docheck: bool = True):
        """Remove mirroring between two channels."""
        if docheck and (not self.bot.get_channel(source_channel_id) or not self.bot.get_channel(dest_channel_id)):
            await ctx.send(inline('Check your channel IDs, or maybe the bot is not in those servers'))
            return
        self.settings.rm_mirrored_channel(source_channel_id, dest_channel_id)
        await ctx.send(inline('Done'))

    @channelmod.command()
    @checks.is_owner()
    async def mirrorconfig(self, ctx):
        """List mirror config."""
        mirrored_channels = self.settings.mirrored_channels()
        msg = 'Mirrored channels\n'
        for mc_id, config in mirrored_channels.items():
            channel = self.bot.get_channel(mc_id)
            channel_name = channel.name if channel else 'unknown'
            msg += '\n{} ({})'.format(mc_id, channel_name)
            for channel_id in config['channels']:
                channel = self.bot.get_channel(channel_id)
                channel_name = channel.name if channel else 'unknown'
                msg += '\n\t{} ({})'.format(channel_id, channel_name)
        await ctx.send(box(msg))

    @commands.Cog.listener('on_message')
    async def mirror_msg_new(self, message):
        if message.author.id == self.bot.user.id or isinstance(message.channel, discord.abc.PrivateChannel):
            return

        channel = message.channel
        mirrored_channels = self.settings.get_mirrored_channels(channel.id)

        if not mirrored_channels:
            return

        last_spoke, last_spoke_timestamp = self.settings.get_last_spoke(channel.id)
        now_time = datetime.utcnow()
        last_spoke_time = datetime.utcfromtimestamp(
            last_spoke_timestamp) if last_spoke_timestamp else now_time
        attribution_required = last_spoke != message.author.id
        attribution_required |= (now_time - last_spoke_time).total_seconds() > ATTRIBUTION_TIME_SECONDS
        self.settings.set_last_spoke(channel.id, message.author.id)

        attachment_bytes = None
        if message.attachments:
            # If we know we're copying a message and that message has an attachment,
            # pre download it and reuse it for every upload.
            attachment = message.attachments[0]
            if hasattr(attachment, 'url') and hasattr(attachment, 'filename'):
                url = attachment.url
                filename = attachment.filename
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        attachment_bytes = io.BytesIO(await response.read())

        for dest_channel_id in mirrored_channels:
            try:
                dest_channel = self.bot.get_channel(dest_channel_id)
                if not dest_channel:
                    continue

                if attribution_required:
                    msg = 'Posted by **{}** in *{} - #{}*:'.format(message.author.name,
                                                                   message.guild.name,
                                                                   message.channel.name)
                    await dest_channel.send(msg)

                if attachment_bytes:
                    dest_message = await dest_channel.send(file=attachment_bytes, filename=filename,
                                                           content=message.content)
                    attachment_bytes.seek(0)
                elif message.content:
                    dest_message = await dest_channel.send(message.content)
                else:
                    print('Failed to mirror message from ', channel.id, 'no action to take')
                    continue

                self.settings.add_mirrored_message(
                    channel.id, message.id, dest_channel.id, dest_message.id)
            except Exception as ex:
                print('Failed to mirror message from ', channel.id, 'to', dest_channel_id, ':', ex)
                traceback.print_exc()

        if attachment_bytes:
            attachment_bytes.close()

    @commands.Cog.listener('on_message_edit')
    async def mirror_msg_edit(self, message, new_message):
        await self.mirror_msg_mod(message, new_message_content=new_message.content)

    @commands.Cog.listener('on_message_delete')
    async def mirror_msg_delete(self, message):
        await self.mirror_msg_mod(message, delete_message_content=True)

    @commands.Cog.listener('on_reaction_add')
    async def mirror_reaction_add(self, reaction, user):
        message = reaction.message
        if message.author.id != user.id:
            return
        await self.mirror_msg_mod(message, new_message_reaction=reaction.emoji)

    @commands.Cog.listener('on_reaction_remove')
    async def mirror_reaction_remove(self, reaction, user):
        message = reaction.message
        if message.author.id != user.id:
            return
        await self.mirror_msg_mod(message, delete_message_reaction=reaction.emoji)

    async def mirror_msg_mod(self, message,
                             new_message_content: str = None,
                             delete_message_content: bool = False,
                             new_message_reaction=None,
                             delete_message_reaction=None):
        if message.author.id == self.bot.user.id or isinstance(message.channel, discord.abc.PrivateChannel):
            return

        channel = message.channel
        mirrored_messages = self.settings.get_mirrored_messages(channel.id, message.id)
        for (dest_channel_id, dest_message_id) in mirrored_messages:
            try:
                dest_channel = self.bot.get_channel(dest_channel_id)
                if not dest_channel:
                    print('could not locate channel to mod')
                    continue
                dest_message = await dest_channel.fetch_message(dest_message_id)
                if not dest_message:
                    print('could not locate message to mod')
                    continue

                if new_message_content:
                    await dest_message.edit(content=new_message_content)
                elif new_message_reaction:
                    await dest_message.add_reaction(new_message_reaction)
                elif delete_message_content:
                    await dest_message.delete()
                elif delete_message_reaction:
                    await dest_message.remove_reaction(delete_message_reaction, dest_message.guild.me)
            except Exception as ex:
                print('Failed to mirror message edit from ',
                      channel.id, 'to', dest_channel_id, ':', ex)


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
        """Returns either None or [(channel_id, message_id), ...]"""
        channel_config = self.mirrored_channels().get(source_channel, None)
        if channel_config:
            return channel_config['messages'].get(source_message, [])
        else:
            return []
