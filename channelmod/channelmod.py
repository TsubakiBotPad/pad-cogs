import asyncio
import io
import logging
import time
import traceback
from _datetime import datetime

import aiohttp
from redbot.core import checks
from redbot.core import commands
from redbot.core.utils.chat_formatting import *

from rpadutils import CogSettings

log = logging.getLogger("red.admin")

INACTIVE = '_inactive'

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
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def channelmod(self, ctx):
        """Manage channel moderation settings"""

    @channelmod.command()
    @checks.mod_or_permissions(manage_channels=True)
    async def inactivemonitor(self, ctx, timeout: int):
        """Enable/disable the activity monitor on this channel.

        Timeout is in seconds. Set to 0 to disable.

        Set the timeout >0 to have the bot automatically append '_inactive' to the channel
        name when the oldest message in the channel is greater than the timeout.
        """
        channel = ctx.channel
        server = channel.guild
        has_permissions = channel.permissions_for(server.me).manage_channels
        if not has_permissions:
            await ctx.send(inline('I need manage channel permissions to do this'))
            return

        self.settings.set_inactivity_monitor_channel(server.id, channel.id, timeout)
        await ctx.send(inline('done'))

    @commands.Cog.listener('on_message')
    async def log_channel_activity_check(self, message):
        if message.author.id == self.bot.user.id or isinstance(message.channel, discord.abc.PrivateChannel):
            return

        server = message.guild
        channel = message.channel
        timeout = self.settings.get_inactivity_monitor_channel_timeout(server.id, channel.id)

        if timeout <= 0:
            return

        self.channel_last_spoke[channel.id] = datetime.utcnow()

        if channel.name.endswith(INACTIVE):
            new_name = channel.name[:-len(INACTIVE)]
            await channel.edit(name=new_name)

    async def check_inactive_channel(self, server_id: int, channel_id: int, timeout: int):
        channel = self.bot.get_channel(int(channel_id))
        if channel is None:
            print('timeout check: cannot find channel', channel_id)
            return

        server = channel.guild

        has_permissions = channel.permissions_for(server.me).manage_channels
        if not has_permissions:
            print('no manage channel permissions, disabling', channel_id)
            self.settings.set_inactivity_monitor_channel(server_id, channel_id, 0)
            return

        now = datetime.utcnow()
        last_spoke_at = self.channel_last_spoke.get(channel.id)
        time_delta = (now - last_spoke_at).total_seconds() if last_spoke_at else 9999
        time_exceeded = time_delta > timeout

        if time_exceeded and not channel.name.endswith(INACTIVE):
            new_name = channel.name + INACTIVE
            try:
                await channel.edit(name=new_name)
            except Exception as ex:
                print('failed to edit channel: ' + str(ex))

    async def check_inactive_channels(self):
        for server_id in self.settings.servers().keys():
            for channel_id, channel_config in self.settings.get_inactivity_monitor_channels(server_id).items():
                timeout = channel_config['timeout']
                if timeout <= 0:
                    continue
                try:
                    await self.check_inactive_channel(server_id, channel_id, timeout)
                except Exception as ex:
                    print('failed to check inactivity channel: ' + str(ex))

    async def channel_inactivity_monitor(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('ChannelMod'):
            try:
                await asyncio.sleep(20)
                await self.check_inactive_channels()
            except:
                traceback.print_exc()

    @channelmod.command()
    @checks.is_owner()
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
            if isinstance(mc_id, str):
                continue
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
        attribution_required |= (
                                        now_time - last_spoke_time).total_seconds() > ATTRIBUTION_TIME_SECONDS
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

    def get_server(self, server_id: str):
        servers = self.servers()
        if server_id not in servers:
            servers[server_id] = {}
        return servers[server_id]

    def get_inactivity_monitor_channels(self, server_id: str):
        server = self.get_server(server_id)
        key = 'inactivity_monitor_channels'
        if key not in server:
            server[key] = {}
        return server[key]

    def set_inactivity_monitor_channel(self, server_id: str, channel_id: str, timeout: int):
        channels = self.get_inactivity_monitor_channels(server_id)
        channels[channel_id] = {'timeout': timeout}
        self.save_settings()

    def get_inactivity_monitor_channel_timeout(self, server_id: str, channel_id: str):
        channels = self.get_inactivity_monitor_channels(server_id)
        channel = channels.get(channel_id, {})
        return channel.get('timeout', 0)

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
        return (spoke_values.get('last_spoke', None), spoke_values.get('last_spoke_timestamp', None))

    def set_last_spoke(self, source_channel: str, last_spoke: str):
        spoke_values = self.mirrored_channels().get(source_channel)
        spoke_values['last_spoke'] = last_spoke
        spoke_values['last_spoke_timestamp'] = time.time()
        self.save_settings()

    def add_mirrored_channel(self, source_channel: str, dest_channel: str):
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

    def rm_mirrored_channel(self, source_channel: str, dest_channel: str):
        channels = self.mirrored_channels()
        config = channels.get(source_channel)
        if config and dest_channel in config['channels']:
            dest_channel_config = config['channels']
            dest_channel_config.remove(dest_channel)
            if not dest_channel_config:
                channels.pop(source_channel)
            self.save_settings()

    def add_mirrored_message(self, source_channel: str, source_message: str, dest_channel: str, dest_message: str):
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

    def get_mirrored_messages(self, source_channel: str, source_message: str):
        """Returns either None or [(channel_id, message_id), ...]"""
        channel_config = self.mirrored_channels().get(source_channel, None)
        if channel_config:
            return channel_config['messages'].get(source_message, [])
        else:
            return []
