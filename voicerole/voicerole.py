from redbot.core import checks
from redbot.core import commands
from redbot.core.utils.chat_formatting import *

from rpadutils import CogSettings, get_role_from_id


class VoiceRole(commands.Cog):
    """Gives a custom to anyone who enters a voice channel. THIS ROLE MUST EXIST AND THE BOT MUST HAVE THE RIGHTS TO CHANGE ROLES FOR IT TO WORK!"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = VoiceRoleSettings("voicerole")

    @commands.Cog.listener("on_voice_state_update")
    async def _on_voice_state_update(self, member, before, after):
        server = member.guild
        server_id = server.id
        channel_id = (before.channel or after.channel).id

        channel_roles = self.settings.getChannelRoles(server_id)
        if channel_id not in channel_roles:
            return

        role_id = channel_roles[channel_id]
        try:
            role = get_role_from_id(self.bot, server, role_id)
            if member.voice:
                await member.add_roles(role)
            else:
                await member.remove_roles(role)
        except Exception as ex:
            print('voicerole failure {} {} {}'.format(server_id, channel_id, role_id))
            print(ex)

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def voicerole(self, ctx):
        """Automatic role adjustment on VC enter/exit."""

    @voicerole.command()
    @commands.guild_only()
    async def set(self, ctx, channel: discord.VoiceChannel, role: discord.Role):
        """Associate a channel with a role.

        To reference a voice channel, use this syntax:
          <#328254327321919489>

        Get the ID by enabling developer tools, right-clicking on the VC, and
        selecting 'copy id'.

        To reference a role, either make it pingable.
        """
        if not isinstance(channel, discord.VoiceChannel):
            await ctx.send('Not a voice channel')
            return

        self.settings.addChannelRole(ctx.guild.id, channel.id, role.id)
        await ctx.send('done')

    @voicerole.command()
    @commands.guild_only()
    async def clear(self, ctx, channel: discord.VoiceChannel):
        """Clear the role associated with a channel"""
        self.settings.rmChannelRole(ctx.guild.id, channel.id)
        await ctx.send('done')

    @voicerole.command()
    @commands.guild_only()
    async def list(self, ctx):
        """List the channel/role associations for this server."""
        msg = 'Channel -> Role:'
        for channel_id, role_id in self.settings.getChannelRoles(ctx.guild.id).items():
            if isinstance(channel_id, int):
                msg += '\n\t{} : {}'.format(channel_id, role_id)
        await ctx.send(box(msg))


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
