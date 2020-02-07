import discord
from discord.ext import commands
import os

from __main__ import user_allowed, send_cmd_help
from cogs.utils.dataIO import dataIO

from .rpadutils import *
from .rpadutils import CogSettings
from .utils import checks
from .utils.chat_formatting import *


class VoiceRole:
    """Gives a custom to anyone who enters a voice channel. THIS ROLE MUST EXIST AND THE BOT MUST HAVE THE RIGHTS TO CHANGE ROLES FOR IT TO WORK!"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = VoiceRoleSettings("voicerole")

    async def _on_voice_state_update(self, before, after):
        member_to_modify = None
        if before.voice_channel is None and after.voice_channel is not None:
            member_to_modify = after
            do_add = True
        elif before.voice_channel is not None and after.voice_channel is None:
            member_to_modify = before
            do_add = False
        else:
            return

        server = member_to_modify.server
        server_id = server.id
        channel_id = member_to_modify.voice_channel.id

        channel_roles = self.settings.getChannelRoles(server_id)
        if channel_id not in channel_roles:
            return

        role_id = channel_roles[channel_id]
        try:
            role = get_role_from_id(self.bot, server, role_id)
            if do_add:
                await self.bot.add_roles(member_to_modify, role)
            else:
                await self.bot.remove_roles(member_to_modify, role)
        except Exception as ex:
            print('voicerole failure {} {} {}'.format(server_id, channel_id, role_id))
            print(ex)

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def voicerole(self, ctx):
        """Automatic role adjustment on VC enter/exit."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @voicerole.command(pass_context=True, no_pm=True)
    async def set(self, ctx, channel: discord.Channel, role: discord.Role):
        """Associate a channel with a role.

        To reference a voice channel, use this syntax:
          <#328254327321919489>

        Get the ID by enabling developer tools, right-clicking on the VC, and
        selecting 'copy id'.

        To reference a role, either make it pingable.
        """
        if channel.type != discord.ChannelType.voice:
            await self.bot.say('Not a voice channel')
            return
        self.settings.addChannelRole(ctx.message.server.id, channel.id, role.id)
        await self.bot.say('done')

    @voicerole.command(pass_context=True, no_pm=True)
    async def clear(self, ctx, channel: discord.Channel):
        """Clear the role associated with a channel"""
        self.settings.rmChannelRole(ctx.message.server.id, channel.id)
        await self.bot.say('done')

    @voicerole.command(pass_context=True, no_pm=True)
    async def list(self, ctx):
        """List the channel/role associations for this server."""
        msg = 'Channel -> Role:'
        for channel_id, role_id in self.settings.getChannelRoles(ctx.message.server.id).items():
            msg += '\n\t{} : {}'.format(channel_id, role_id)
        await self.bot.say(box(msg))


def setup(bot):
    n = VoiceRole(bot)
    bot.add_listener(n._on_voice_state_update, 'on_voice_state_update')
    bot.add_cog(n)


class VoiceRoleSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'servers': {}
        }
        return config

    def serverConfigs(self):
        return self.bot_settings['servers']

    def getServer(self, server_id):
        configs = self.serverConfigs()
        if server_id not in configs:
            configs[server_id] = {}
        return configs[server_id]

    def getChannelRoles(self, server_id):
        key = 'channel_ids'
        server = self.getServer(server_id)
        if key not in server:
            server[key] = {}
        return server[key]

    def addChannelRole(self, server_id, channel_id, role_id):
        channel_roles = self.getChannelRoles(server_id)
        channel_roles[channel_id] = role_id
        self.save_settings()

    def rmChannelRole(self, server_id, channel_id):
        channel_roles = self.getChannelRoles(server_id)
        if channel_id in channel_roles:
            channel_roles.pop(channel_id)
            self.save_settings()
