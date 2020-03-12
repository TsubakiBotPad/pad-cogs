import asyncio
import random
import traceback

import discord
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import inline, box

from rpadutils import CogSettings, get_role, get_role_from_id


class StreamCopy(commands.Cog):
    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = StreamCopySettings("streamcopy")
        self.current_user_id = None

    async def refresh_stream(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog('StreamCopy'):
            try:
                await self.do_refresh()
                await self.do_ensure_roles()
            except Exception as e:
                traceback.print_exc()

            await asyncio.sleep(60 * 3)
        print("done refresh_stream")

    @commands.group()
    @checks.mod_or_permissions(manage_guild=True)
    async def streamcopy(self, ctx):
        """Utilities for reacting to users gaining/losing streaming status."""

    @streamcopy.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def setStreamerRole(self, ctx, *, role_name: str):
        try:
            role = get_role(ctx.guild.roles, role_name)
        except:
            await ctx.send(inline('Unknown role'))
            return

        self.settings.set_streamer_role(ctx.guild.id, role.id)
        await ctx.send(inline('Done. Make sure that role is below the bot in the hierarchy'))

    @streamcopy.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def clearStreamerRole(self, ctx):
        self.settings.clear_streamer_role(ctx.guild.id)
        await self.bot.say(inline('Done'))

    @streamcopy.command(name="adduser")
    @checks.is_owner()
    async def addUser(self, ctx, user: discord.User):
        self.settings.add_user(user.id)
        await ctx.send(inline('Done'))

    @streamcopy.command(name="rmuser")
    @checks.is_owner()
    async def rmUser(self, ctx, user: discord.User):
        self.settings.rm_user(user.id)
        await ctx.send(inline('Done'))

    @streamcopy.command(name="list")
    @checks.is_owner()
    async def list(self, ctx):
        user_ids = self.settings.users().keys()
        members = {x.id: x for x in self.bot.get_all_members() if x.id in user_ids}

        output = "Users:"
        for m_id, m in members.items():
            output += "\n({}) : {}".format('+' if self.is_playing(m) else '-', m.name)

        await ctx.send(box(output))

    @streamcopy.command(name="refresh")
    @checks.is_owner()
    async def refresh(self, ctx):
        other_stream = await self.do_refresh()
        if other_stream:
            await ctx.send(inline('Updated stream'))
        else:
            await ctx.send(inline('Could not find a streamer'))

    async def check_stream(self, before, after):
        streamer_role_id = self.settings.get_streamer_role(before.guild.id)
        if streamer_role_id:
            await self.ensure_user_streaming_role(after.guild, streamer_role_id, after)

        try:
            tracked_users = self.settings.users()
            if before.id not in tracked_users:
                return

            if self.is_playing(after):
                await self.copy_playing(after.activity)
                return

            await self.do_refresh()
        except Exception as ex:
            print("Stream checking failed", ex)

    async def ensure_user_streaming_role(self, server, streamer_role_id: discord.Role, user: discord.Member):
        user_is_playing = self.is_playing(user)
        try:
            streamer_role = get_role_from_id(self.bot, server, streamer_role_id)
            user_has_streamer_role = streamer_role in user.roles
            if user_is_playing and not user_has_streamer_role:
                await user.add_roles(streamer_role)
            elif not user_is_playing and user_has_streamer_role:
                await user.remove_roles(streamer_role)
        except Exception as ex:
            pass

    async def do_refresh(self):
        other_stream = self.find_stream()
        if other_stream:
            await self.copy_playing(other_stream)
        else:
            await self.bot.change_presence(activity=None)
        return other_stream

    async def do_ensure_roles(self):
        servers = self.bot.guilds
        for server in servers:
            streamer_role_id = self.settings.get_streamer_role(server.id)
            if not streamer_role_id:
                continue
            for member in server.members:
                await self.ensure_user_streaming_role(member.guilds, streamer_role_id, member)

    def find_stream(self):
        user_ids = self.settings.users().keys()
        members = {x.id: x for x in self.bot.get_all_members() if x.id in user_ids and self.is_playing(x)}
        games = [x.activity for x in members.values()]
        random.shuffle(games)
        return games[0] if len(games) else None

    def is_playing(self, member: discord.Member):
        return member and member.activity and member.activity.type == 1 and member.activity.url

    async def copy_playing(self, stream: discord.Streaming):
        new_stream = discord.Game(name=stream.name, url=stream.url, type=stream.type)
        await self.bot.change_presence(activity=new_stream)


class StreamCopySettings(CogSettings):
    def make_default_settings(self):
        config = {
            'users': {},
            'servers': {}
        }
        return config

    def users(self):
        return self.bot_settings['users']

    def add_user(self, user_id):
        users = self.users()
        users[user_id] = {'priority': 100}  # This is for stupid legacy reasons
        self.save_settings()

    def rm_user(self, user_id):
        users = self.users()
        if user_id in users:
            users.pop(user_id)
            self.save_settings()

    def get_guild(self, guild_id):
        guilds = self.bot_settings['servers']
        if guild_id not in guilds:
            guilds[guild_id] = {}
        return guilds[guild_id]

    def set_streamer_role(self, server_id, role_id):
        server = self.get_guild(server_id)
        server['role'] = role_id
        self.save_settings()

    def get_streamer_role(self, server_id):
        server = self.get_guild(server_id)
        return server.get('role', None)

    def clear_streamer_role(self, server_id):
        server = self.get_guild(server_id)
        if 'role' in server:
            server.pop('role')
            self.save_settings()
