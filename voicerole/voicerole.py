from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import *

from rpadutils import CogSettings, get_role_from_id


class VoiceRole(commands.Cog):
    """Gives a custom to anyone who enters a voice channel.

    THIS ROLE MUST EXIST AND THE BOT MUST HAVE THE RIGHTS TO CHANGE ROLES FOR IT TO WORK!
    """

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = VoiceRoleSettings("voicerole")

    @commands.Cog.listener("on_voice_state_update")
    async def _on_voice_state_update(self, member, before, after):
        guild = member.guild
        guild_id = guild.id
        channel_id = (before.channel or after.channel).id

        channel_roles = self.settings.get_channel_roles(guild_id)
        if channel_id not in channel_roles:
            return

        role_id = channel_roles[channel_id]
        try:
            role = get_role_from_id(self.bot, guild, role_id)
            if member.voice:
                await member.add_roles(role)
            else:
                await member.remove_roles(role)
        except Exception as ex:
            print('voicerole failure {} {} {}'.format(guild_id, channel_id, role_id))
            print(ex)

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def voicerole(self, ctx):
        """Automatic role adjustment on VC enter/exit."""
        pass

    @voicerole.command()
    async def set(self, ctx, channel: discord.VoiceChannel, role: discord.Role):
        """Associate a channel with a role.

        To reference a voice channel, use this syntax:
          <#328254327321919489>

        Get the ID by enabling developer tools, right-clicking on the VC, and
        selecting 'copy id'.

        To reference a role, make it pingable.
        """
        self.settings.add_channel_role(ctx.guild.id, channel.id, role.id)
        await ctx.send('done')

    @voicerole.command()
    async def clear(self, ctx, channel: discord.VoiceChannel):
        """Clear the role associated with a channel"""
        self.settings.rm_channel_role(ctx.guild.id, channel.id)
        await ctx.send('done')

    @voicerole.command()
    async def list(self, ctx):
        """List the channel/role associations for this server."""
        msg = 'Channel -> Role:'
        for channel_id, role_id in self.settings.get_channel_roles(ctx.guild.id).items():
            msg += '\n\t{} : {}'.format(channel_id, role_id)
        await ctx.send(box(msg))


class VoiceRoleSettings(CogSettings):
    def make_default_settings(self):
        config = {
            'servers': {}
        }
        return config

    def guild_configs(self):
        return self.bot_settings['servers']

    def get_guild(self, guild_id):
        configs = self.guild_configs()
        if guild_id not in configs:
            configs[guild_id] = {}
        return configs[guild_id]

    def get_channel_roles(self, guild_id):
        key = 'channel_ids'
        guild = self.get_guild(guild_id)
        if key not in guild:
            guild[key] = {}
        return guild[key]

    def add_channel_role(self, server_id, channel_id, role_id):
        channel_roles = self.get_channel_roles(server_id)
        channel_roles[channel_id] = role_id
        self.save_settings()

    def rm_channel_role(self, guild_id, channel_id):
        channel_roles = self.get_channel_roles(guild_id)
        if channel_id in channel_roles:
            channel_roles.pop(channel_id)
            self.save_settings()
