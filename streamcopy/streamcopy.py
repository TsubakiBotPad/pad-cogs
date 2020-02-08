import asyncio
from collections import defaultdict
from collections import deque
import copy
import os
import random
import re
from time import time
import traceback

import discord
from discord.ext import commands

from __main__ import send_cmd_help
from __main__ import settings

from .rpadutils import *
from .rpadutils import CogSettings
from .utils import checks
from .utils.dataIO import fileIO
from .utils.settings import Settings


class StreamCopy(commands.Cog):
    def __init__(self, bot):
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

    @commands.group(pass_context=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def streamcopy(self, context):
        """Utilities for reacting to users gaining/losing streaming status."""
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @streamcopy.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def setStreamerRole(self, ctx, *, role_name: str):
        try:
            role = get_role(ctx.message.server.roles, role_name)
        except:
            await self.bot.say(inline('Unknown role'))
            return

        self.settings.setStreamerRole(ctx.message.server.id, role.id)
        await self.bot.say(inline('Done. Make sure that role is below the bot in the hierarchy'))

    @streamcopy.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_guild=True)
    async def clearStreamerRole(self, ctx):
        self.settings.clearStreamerRole(ctx.message.server.id)
        await self.bot.say(inline('Done'))

    @streamcopy.command(name="adduser", pass_context=True)
    @checks.is_owner()
    async def addUser(self, ctx, user: discord.User, priority: int):
        self.settings.addUser(user.id, priority)
        await self.bot.say(inline('Done'))

    @streamcopy.command(name="rmuser", pass_context=True)
    @checks.is_owner()
    async def rmUser(self, ctx, user: discord.User):
        self.settings.rmUser(user.id)
        await self.bot.say(inline('Done'))

    @streamcopy.command(name="list", pass_context=True)
    @checks.is_owner()
    async def list(self, ctx):
        user_ids = self.settings.users().keys()
        members = {x.id: x for x in self.bot.get_all_members() if x.id in user_ids}

        output = "Users:"
        for m_id, m in members.items():
            output += "\n({}) : {}".format('+' if self.is_playing(m) else '-', m.name)

        await self.bot.say(box(output))

    @streamcopy.command(name="refresh")
    @checks.is_owner()
    async def refresh(self):
        other_stream = await self.do_refresh()
        if other_stream:
            await self.bot.say(inline('Updated stream'))
        else:
            await self.bot.say(inline('Could not find a streamer'))

    async def check_stream(self, before, after):
        streamer_role_id = self.settings.getStreamerRole(before.server.id)
        if streamer_role_id:
            await self.ensure_user_streaming_role(after.server, streamer_role_id, after)

        try:
            tracked_users = self.settings.users()
            if before.id not in tracked_users:
                return

            if self.is_playing(after):
                await self.copy_playing(after.game)
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
                await self.bot.add_roles(user, streamer_role)
            elif not user_is_playing and user_has_streamer_role:
                await self.bot.remove_roles(user, streamer_role)
        except ex:
            pass

    async def do_refresh(self):
        other_stream = self.find_stream()
        if other_stream:
            await self.copy_playing(other_stream)
        else:
            await self.bot.change_presence(game=None)
        return other_stream

    async def do_ensure_roles(self):
        servers = self.bot.servers
        for server in servers:
            streamer_role_id = self.settings.getStreamerRole(server.id)
            if not streamer_role_id:
                continue
            for member in server.members:
                await self.ensure_user_streaming_role(member.server, streamer_role_id, member)

    def find_stream(self):
        user_ids = self.settings.users().keys()
        members = {x.id: x for x in self.bot.get_all_members(
        ) if x.id in user_ids and self.is_playing(x)}
        games = [x.game for x in members.values()]
        random.shuffle(games)
        return games[0] if len(games) else None

    def is_playing(self, member: discord.Member):
        return member and member.game and member.game.type == 1 and member.game.url

    async def copy_playing(self, game: discord.Game):
        new_game = discord.Game(name=game.name, url=game.url, type=game.type)
        await self.bot.change_presence(game=new_game)


def setup(bot):
    n = StreamCopy(bot)
    bot.add_listener(n.check_stream, "on_member_update")
    bot.loop.create_task(n.refresh_stream())
    bot.add_cog(n)


class StreamCopySettings(CogSettings):
    def make_default_settings(self):
        config = {
            'users': {},
            'servers': {}
        }
        return config

    def users(self):
        return self.bot_settings['users']

    def addUser(self, user_id, priority):
        users = self.users()
        users[user_id] = {'priority': priority}
        self.save_settings()

    def rmUser(self, user_id):
        users = self.users()
        if user_id in users:
            users.pop(user_id)
            self.save_settings()

    def servers(self, server_id):
        servers = self.bot_settings['servers']
        if server_id not in servers:
            servers[server_id] = {}
        return servers[server_id]

    def setStreamerRole(self, server_id, role_id):
        server = self.servers(server_id)
        server['role'] = role_id
        self.save_settings()

    def getStreamerRole(self, server_id):
        server = self.servers(server_id)
        return server.get('role', None)

    def clearStreamerRole(self, server_id):
        server = self.servers(server_id)
        if 'role' in server:
            server.pop('role')
            self.save_settings()
