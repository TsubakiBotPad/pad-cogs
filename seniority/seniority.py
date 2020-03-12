import os
import re
import sys
import timeit
from collections import deque
from datetime import datetime, timedelta

import aioodbc
import discord
import prettytable
import pytz
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import inline, pagify, box

import rpadutils
from rpadutils import CogSettings, NA_TZ_OBJ

CREATE_TABLE = '''
CREATE TABLE IF NOT EXISTS seniority(
  record_date STRING NOT NULL,
  server_id STRING NOT NULL,
  channel_id STRING NOT NULL,
  user_id STRING NOT NULL,
  points REAL DEFAULT 0,
  PRIMARY KEY (record_date, server_id, channel_id, user_id))
'''

CREATE_INDEX_1 = '''
CREATE INDEX IF NOT EXISTS idx_server_id_record_date_user_id
ON seniority(server_id, record_date, user_id)
'''

# Why?
CREATE_INDEX_2 = '''
CREATE INDEX IF NOT EXISTS idx_record_date_server_id_user_id
ON seniority(record_date, server_id, user_id)
'''

# Why? record date should never come first
CREATE_INDEX_3 = '''
CREATE INDEX IF NOT EXISTS idx_record_date_server_id_channel_id_user_id
ON seniority(record_date, server_id, channel_id, user_id)
'''

CREATE_INDEX_4 = '''
CREATE INDEX IF NOT EXISTS idx_server_id_user_id_record_date
ON seniority(server_id, user_id, record_date)
'''

GET_USER_POINTS_QUERY = '''
SELECT record_date, round(sum(points), 2) as points
FROM seniority INDEXED BY idx_server_id_user_id_record_date
WHERE server_id = ?
  AND user_id = ?
GROUP BY 1
ORDER BY 1 DESC
LIMIT ?
'''

GET_LOOKBACK_POINTS_QUERY = '''
SELECT user_id, sum(points) as points
FROM seniority INDEXED BY idx_server_id_user_id_record_date
WHERE server_id = ?
  AND record_date >= ?
GROUP BY 1
'''

GET_DATE_POINTS_QUERY = '''
SELECT channel_id, points
FROM seniority INDEXED BY idx_server_id_record_date_user_id
WHERE record_date = ?
  AND server_id = ?
  AND user_id = ?
'''

GET_NEWMESSAGE_POINTS_QUERY = '''
SELECT SUM(points) as points
FROM seniority INDEXED BY idx_record_date_server_id_channel_id_user_id
WHERE record_date = ?
  AND server_id = ?
  AND channel_id = ?
  AND user_id = ?
'''

GET_NEWMESSAGE_SERVER_POINTS_QUERY = '''
SELECT SUM(points) as points
FROM seniority INDEXED BY idx_record_date_server_id_user_id
WHERE record_date = ?
  AND server_id = ?
  AND user_id = ?
'''

REPLACE_POINTS_QUERY = '''
REPLACE INTO seniority(record_date, server_id, channel_id, user_id, points)
VALUES(?, ?, ?, ?, ?)
'''

DELETE_DAY_QUERY = '''
DELETE FROM seniority
WHERE record_date = ?
  AND server_id = ?
'''


class Seniority(commands.Cog):
    """Automatically promote people based on activity."""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = SenioritySettings("seniority")
        self.db_path = self.settings.folder + '/log.db'
        self.lock = True
        self.pool = None
        self.insert_timing = deque(maxlen=1000)

    def cog_unload(self):
        print('Seniority: unloading')
        self.lock = True
        if self.pool:
            self.pool.close()
            self.pool = None
        else:
            print('unexpected error: pool was None')
        print('Seniority: unloading complete')

    async def init(self):
        print('Seniority: init')
        if not self.lock:
            print('Seniority: bailing on unlock')
            return

        if os.name != 'nt' and sys.platform != 'win32':
            dsn = 'Driver=SQLite3;Database=' + self.db_path
        else:
            dsn = 'Driver=SQLite3 ODBC Driver;Database=' + self.db_path
        self.pool = await aioodbc.create_pool(dsn=dsn, autocommit=True)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(CREATE_TABLE)
                await cur.execute(CREATE_INDEX_1)
                await cur.execute(CREATE_INDEX_2)
                await cur.execute(CREATE_INDEX_3)
                await cur.execute(CREATE_INDEX_4)
        self.lock = False

        print('Seniority: init complete')

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def seniority(self, ctx):
        """Automatically promote people based on activity."""

    @seniority.command()
    @checks.is_owner()
    async def rawquery(self, ctx, *, query: str):
        await self.queryAndPrint(ctx, ctx.guild, query, [])

    @seniority.command()
    @checks.is_owner()
    async def inserttiming(self, ctx):
        size = len(self.insert_timing)
        avg_time = round(sum(self.insert_timing) / size, 4)
        max_time = round(max(self.insert_timing), 4)
        min_time = round(min(self.insert_timing), 4)
        await ctx.send(inline('{} inserts, min={} max={} avg={}'.format(size, min_time, max_time, avg_time)))

    @seniority.command()
    @checks.is_owner()
    async def togglelock(self, ctx):
        self.lock = not self.lock
        await ctx.send(inline('Locked is now {}'.format(self.lock)))

    @seniority.command()
    @commands.guild_only()
    async def printconfig(self, ctx):
        """Print the configuration for the server."""
        server = ctx.guild
        server_id = server.id
        msg = 'Config:'
        announce_channel = self.get_announce_channel(server_id)
        msg += '\n\tannounce_channel: {}'.format(
            announce_channel.name if announce_channel else '<unset>')
        msg += '\n\tauto_grant: {}'.format(self.settings.auto_grant(server_id))
        msg += '\n\tmessage_cap: {}'.format(self.settings.message_cap(server_id))
        msg += '\n\tserver_point_cap: {}'.format(self.settings.server_point_cap(server_id))
        msg += '\n\tgrant_lookback: {}'.format(self.settings.grant_lookback(server_id))
        msg += '\n\tremove_lookback: {}'.format(self.settings.remove_lookback(server_id))
        msg += '\n\n'
        msg += 'Acceptability:'
        msg += '\n\tignore_commands: {}'.format(self.settings.ignore_commands(server_id))
        msg += '\n\tignore_emoji: {}'.format(self.settings.ignore_emoji(server_id))
        msg += '\n\tignore_mentions: {}'.format(self.settings.ignore_mentions(server_id))
        msg += '\n\tignore_room_codes: {}'.format(self.settings.ignore_room_codes(server_id))
        msg += '\n\tmin_length: {}'.format(self.settings.min_length(server_id))
        msg += '\n\tmin_words: {}'.format(self.settings.min_words(server_id))
        msg += '\n\n'
        msg += 'Ignored Users:'
        for user_id in self.settings.blacklist(server_id):
            member = server.get_member(int(user_id))
            msg += '\n\t{} ({})'.format(member.name if member else 'unknown', user_id)
        msg += '\n\n'
        msg += 'Channels and max ppd:'
        for channel_id, config in self.settings.channels(server_id).items():
            channel = self.bot.get_channel(int(channel_id))
            msg += '\n\t{} : {}'.format(channel.name if channel else channel_id, config['max_ppd'])
        msg += '\n\n'
        msg += 'Roles:'
        for role_id, config in self.settings.roles(server_id).items():
            try:
                role = rpadutils.get_role_from_id(self.bot, server, role_id)
                role_name = role.name
            except:
                role_name = role_id
            msg += '\n\t{}'.format(role_name)
            msg += '\n\t\tremove_amount : {}'.format(config['remove_amount'])
            msg += '\n\t\twarn_amount : {}'.format(config['warn_amount'])
            msg += '\n\t\tgrant_amount : {}'.format(config['grant_amount'])

        for page in pagify(msg):
            await ctx.send(box(page))

    def get_announce_channel(self, server_id):
        announce_channel_id = self.settings.announce_channel(server_id)
        return self.bot.get_channel(announce_channel_id)

    @seniority.group()
    @commands.guild_only()
    async def grant(self, ctx):
        """Seniority grant and remove actions."""

    @grant.command()
    @commands.guild_only()
    async def listbelow(self, ctx):
        """List users below the remove amount."""
        lookback_days = self.settings.remove_lookback(ctx.guild.id)
        await self.do_print_overages(ctx, ctx.guild, lookback_days, 'remove_amount', False)

    @grant.command()
    @commands.guild_only()
    async def listnear(self, ctx):
        """List users above the warn amount."""
        lookback_days = self.settings.grant_lookback(ctx.guild.id)
        await self.do_print_overages(ctx, ctx.guild, lookback_days, 'warn_amount', True)

    @grant.command()
    @commands.guild_only()
    async def listover(self, ctx):
        """List users above the grant amount."""
        lookback_days = self.settings.grant_lookback(ctx.guild.id)
        await self.do_print_overages(ctx, ctx.guild, lookback_days, 'grant_amount', True)

    @grant.command()
    @commands.guild_only()
    async def grantnow(self, ctx):
        """List users above the grant amount."""
        guild = ctx.guild
        lookback_days = self.settings.grant_lookback(guild.id)
        for role_id, role, amount in self.roles_and_amounts(guild, 'grant_amount'):
            if role is None or amount <= 0:
                continue

            msg = 'Granting for role {} (point cutoff {})'.format(role.name, amount)
            await ctx.send(inline(msg))

            grant_users, ignored_users = await self.get_grant_ignore_users(
                guild, role, amount, lookback_days, True)
            grant_users = [guild.get_member(int(x[0])) for x in grant_users]

            cs = 5
            user_chunks = [grant_users[i:i + cs] for i in range(0, len(grant_users), cs)]
            for chunk in user_chunks:
                msg = 'Granting to users: ' + ','.join([m.name for m in chunk])
                await ctx.send(inline(msg))
                for member in chunk:
                    try:
                        await member.add_roles(role)
                    except Exception as ex:
                        raise commands.UserFeedbackCheckFailure(str(ex))

    @grant.command()
    @commands.guild_only()
    async def removenow(self, ctx):
        """List users below the remove amount."""
        server = ctx.guild
        lookback_days = self.settings.remove_lookback(server.id)
        for role_id, role, amount in self.roles_and_amounts(server, 'remove_amount'):
            if role is None or amount <= 0:
                continue

            msg = 'Removing for role {} (point cutoff {})'.format(role.name, amount)
            await ctx.send(inline(msg))

            grant_users, ignored_users = await self.get_grant_ignore_users(
                server, role, amount, lookback_days, False)
            grant_users = [server.get_member(int(x[0])) for x in grant_users]

            cs = 5
            user_chunks = [grant_users[i:i + cs] for i in range(0, len(grant_users), cs)]
            for chunk in user_chunks:
                msg = 'Removing from users: ' + ','.join([m.name for m in chunk])
                await ctx.send(inline(msg))
                for member in chunk:
                    try:
                        await member.remove_roles(role)
                    except Exception as ex:
                        raise commands.UserFeedbackCheckFailure(str(ex))

    async def do_print_overages(self,
                                ctx: Context,
                                server: discord.Guild,
                                lookback_days: int,
                                check_name: str,
                                points_greater_than: bool):
        await ctx.send(inline('Printing info for all roles'))

        for role_id, role, amount in self.roles_and_amounts(server, check_name):
            if role is None:
                await ctx.send(inline('Cannot find role with id ' + role_id))
                continue

            if amount <= 0:
                await ctx.send(inline('Skipping role {} (disabled)'.format(role.name)))
                continue

            grant_users, ignored_users = await self.get_grant_ignore_users(
                server, role, amount, lookback_days, points_greater_than)

            def process_userlist(user_list):
                r = ''
                for userid_points in user_list:
                    user_id = userid_points[0]
                    member = server.get_member(int(user_id))
                    member_name = member.name if member else user_id
                    points = round(userid_points[1], 2)
                    r += '\n\t{} ({}) : {}'.format(member_name, user_id, points)
                return r

            msg = 'Modified users for role {} (point cutoff {})'.format(role.name, amount)
            msg += process_userlist(grant_users)
            msg += '\n\nIgnored users'
            msg += process_userlist(ignored_users)

            for page in pagify(msg):
                await ctx.send(box(page))

    def roles_and_amounts(self, server: discord.Guild, check_name: str):
        for role_id, role_config in self.settings.roles(server.id).items():
            amount = role_config[check_name]
            try:
                role = rpadutils.get_role_from_id(self.bot, server, role_id)
            except:
                role = None
            yield role_id, role, amount

    async def get_grant_ignore_users(self,
                                     server: discord.Guild,
                                     role: discord.Role,
                                     amount: int,
                                     lookback_days: int,
                                     points_greater_than: bool):

        if points_greater_than:
            def point_check_fn(p):
                return p >= amount
        else:
            def point_check_fn(p):
                return p < amount

        users_and_points = await self.get_lookback_points(server, lookback_days)
        grant_users, ignored_users = self.check_users_for_role(
            users_and_points, server, point_check_fn, role, points_greater_than)

        return grant_users, ignored_users

    async def get_lookback_points(self, server: discord.Guild, lookback_days: int):
        lookback_date = datetime.now(rpadutils.NA_TZ_OBJ) - timedelta(days=lookback_days)
        lookback_date_str = lookback_date.date().isoformat()

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(GET_LOOKBACK_POINTS_QUERY, server.id, lookback_date_str)
                rows = await cur.fetchall()
                return [(int(x[0]), x[1]) for x in rows]

    def check_users_for_role(self,
                             users_and_points,
                             server: discord.Guild,
                             point_check_fn,
                             role: discord.Role,
                             adding_role: bool):
        blacklisted_ids = self.settings.blacklist(server.id).keys()

        grant_users = []
        ignored_users = []

        userid_to_points = {x[0]: x[1] for x in users_and_points}
        for user in server.members:
            points = userid_to_points.get(user.id, 0)
            if role in user.roles and adding_role:
                continue
            if role not in user.roles and not adding_role:
                continue
            if not point_check_fn(points):
                continue

            if user.id in blacklisted_ids:
                ignored_users.append((user.id, points))
            else:
                grant_users.append((user.id, points))

        return grant_users, ignored_users

    @seniority.command()
    @commands.guild_only()
    async def userhistory(self, ctx, user: discord.User, limit=30):
        """Print the points per day for a user."""
        limit = min(limit, 90)
        server = ctx.guild
        args = [server.id, user.id, limit]
        await self.queryAndPrint(ctx, server, GET_USER_POINTS_QUERY, args, reverse=True, total=True)

    @seniority.command()
    @commands.guild_only()
    async def usercurrent(self, ctx, user: discord.User):
        """Print the current day's points for a user."""
        server = ctx.guild
        args = [now_date(), server.id, user.id]
        await self.queryAndPrint(ctx, server, GET_DATE_POINTS_QUERY, args)

    @seniority.command()
    @commands.guild_only()
    async def blacklist(self, ctx, user: discord.User, reason: str):
        """Ensure a user never gets a role auto granted."""
        server = ctx.guild
        by = ctx.author
        self.settings.add_blacklist(server.id, user.id, by.id, reason)
        await ctx.send(inline('Set blacklist'))

    @seniority.command()
    @commands.guild_only()
    async def unblacklist(self, ctx, user: discord.User):
        """Remove the blacklist for a user."""
        server = ctx.guild
        if self.settings.remove_blacklist(server.id, user.id):
            await ctx.send(inline('Removed blacklist'))
        else:
            await ctx.send(inline('That user was not blacklisted'))

    @seniority.command()
    @commands.guild_only()
    async def checktext(self, ctx, text: str):
        """Check if text is considered significant by the current config.
        """
        is_good, cleaned_text, reason = await self.check_acceptable(ctx.message, text)
        if is_good:
            await ctx.send(box('Message accepted, cleaned text:\n{}'.format(cleaned_text)))
        else:
            await ctx.send(box('Message rejected ({}), cleaned text:\n{}'.format(reason, cleaned_text)))

    @seniority.group()
    @commands.guild_only()
    async def config(self, ctx):
        """Toggle Seniority configuration settings."""
        pass

    @config.command()
    @commands.guild_only()
    async def announcechannel(self, ctx, channel: discord.TextChannel):
        """Set the announcement channel."""
        self.settings.set_announce_channel(ctx.guild.id, channel.id)
        await ctx.send(inline('Done.'))

    @config.command()
    @commands.guild_only()
    async def messagecap(self, ctx, cap_amount: int):
        """Set the number of messages required to reach maximum points for a channel."""
        self.settings.set_message_cap(ctx.guild.id, cap_amount)
        await ctx.send(inline('Done.'))

    @config.command()
    @commands.guild_only()
    async def serverpointcap(self, ctx, cap_amount: int):
        """Set the maximum number of points per day a user can receive in the server."""
        self.settings.set_server_point_cap(ctx.guild.id, cap_amount)
        await ctx.send(inline('Done.'))

    @config.command()
    @commands.guild_only()
    async def toggleautogrant(self, ctx):
        """Enable or disable the automatic granting of roles."""
        server_id = ctx.guild.id
        new_setting = not self.settings.auto_grant(server_id)
        self.settings.set_auto_grant(server_id, new_setting)
        await ctx.send(inline('Auto grant set to {}.'.format(new_setting)))

    @config.command()
    @commands.guild_only()
    async def grantlookback(self, ctx, days: int):
        """Number of days to look back when computing points for granting a role."""
        server_id = ctx.guild.id
        self.settings.set_grant_lookback(server_id, days)
        await ctx.send(inline('Grant lookback set to {}.'.format(days)))

    @config.command()
    @commands.guild_only()
    async def removelookback(self, ctx, days: int):
        """Number of days to look back when computing points for removing a role."""
        server_id = ctx.guild.id
        self.settings.set_remove_lookback(server_id, days)
        await ctx.send(inline('Remove lookback set to {}.'.format(days)))

    @config.command()
    @commands.guild_only()
    async def channel(self, ctx, channel: discord.TextChannel, max_points_per_day: int):
        """Maximum points per day a user can earn in a channel (0 disables)."""
        server_id = ctx.guild.id
        self.settings.set_channel(server_id, channel.id, max_points_per_day)
        if max_points_per_day:
            await ctx.send(inline('Max points set to {}.'.format(max_points_per_day)))
        else:
            await ctx.send(inline('Channel disabled'))

    @config.command()
    @commands.guild_only()
    async def role(self, ctx, role_name: str, remove_amount: int, warn_amount: int, grant_amount: int):
        """Set the configuration for a role.

        role_name: Role name to configure
        remove_amount: Automatic role removal threshold. Set to 0 to disable.
        warn_amount: Print a warning in the announcement channel when exceeded. Set to 0 to disable.
        grant_amount: Automatic role grant threshold. Set to 0 to disable.

        remove_amount must be less than grant_amount.
        Set all three to 0 to delete the entry.
        """
        server = ctx.guild
        role = rpadutils.get_role(server.roles, role_name)
        self.settings.set_role(server.id, role.id, remove_amount, warn_amount, grant_amount)

        if remove_amount == 0 and grant_amount == 0:
            await ctx.send(inline('Role configuration deleted'))
            return

        msg = 'Done.'
        if remove_amount <= 0:
            msg += '\nThis role will not be automatically removed.'
        else:
            msg += '\nThis role will be removed when points in remove window drop below {}.'.format(
                remove_amount)
        if grant_amount <= 0:
            msg += '\nThis role will not be automatically granted.'
        else:
            if warn_amount <= 0:
                msg += '\nNo early warning will be given for this role.'
            else:
                msg += '\nI will warn when a user exceeds {} points in the grant window.'.format(
                    warn_amount)
            msg += '\nThis role will be granted when points in grant window exceed {}.'.format(
                grant_amount)

        await ctx.send(box(msg))

    @seniority.group()
    @commands.guild_only()
    async def acceptable(self, ctx):
        """Toggle Seniority text acceptability settings."""

    @acceptable.command()
    @commands.guild_only()
    async def togglecommands(self, ctx):
        """Toggle rejection of bot commands."""
        server_id = ctx.guild.id
        new_setting = not self.settings.ignore_commands(server_id)
        self.settings.set_ignore_commands(server_id, new_setting)
        await ctx.send(inline('ignore_commands set to {}.'.format(new_setting)))

    @acceptable.command()
    @commands.guild_only()
    async def toggleemoji(self, ctx):
        """Toggle deletion of emoji from text."""
        server_id = ctx.guild.id
        new_setting = not self.settings.ignore_emoji(server_id)
        self.settings.set_ignore_emoji(server_id, new_setting)
        await ctx.send(inline('ignore_emoji set to {}.'.format(new_setting)))

    @acceptable.command()
    @commands.guild_only()
    async def togglementions(self, ctx):
        """Toggle deletion of mentions from text."""
        server_id = ctx.guild.id
        new_setting = not self.settings.ignore_mentions(server_id)
        self.settings.set_ignore_mentions(server_id, new_setting)
        await ctx.send(inline('ignore_mentions set to {}.'.format(new_setting)))

    @acceptable.command()
    @commands.guild_only()
    async def toggleroomcodes(self, ctx):
        """Toggle rejection of text containing room codes."""
        server_id = ctx.guild.id
        new_setting = not self.settings.ignore_room_codes(server_id)
        self.settings.set_ignore_room_codes(server_id, new_setting)
        await ctx.send(inline('ignore_room_codes set to {}.'.format(new_setting)))

    @acceptable.command()
    @commands.guild_only()
    async def minlength(self, ctx, length: int):
        """Set the minimum length of text."""
        server_id = ctx.guild.id
        self.settings.set_min_length(server_id, length)
        await ctx.send(inline('Min text length set to {}.'.format(length)))

    @acceptable.command()
    @commands.guild_only()
    async def minwords(self, ctx, words: int):
        """Set the minimum number of words in text."""
        server_id = ctx.guild.id
        self.settings.set_min_words(server_id, words)
        await ctx.send(inline('Min word count set to {}.'.format(words)))

    async def check_acceptable(self, message: discord.Message, text: str):
        server = message.guild
        server_id = server.id
        if self.settings.ignore_commands(server_id):
            if await rpadutils.get_prefix(self.bot, message):
                return False, text, 'Ignored command'

        if self.settings.ignore_room_codes(server_id):
            if re.match(r'.*\d{4}\s?\d{4}.*', text):
                return False, text, 'Ignored room code'

        if self.settings.ignore_emoji(server_id):
            text = re.sub(r'<:[0-9a-z_]+:\d{18}>', '', text, re.IGNORECASE)

        if self.settings.ignore_mentions(server_id):
            text = re.sub(r'<@\d{18}>', '', text, re.IGNORECASE)

        if len(text) < self.settings.min_length(server_id):
            return False, text, 'Min length'

        if len(text.split()) < self.settings.min_words(server_id):
            return False, text, 'Min words'

        return True, text, 'Passed!'

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return
        now_date_str = now_date()
        await self.process_message(message, now_date_str)

    async def process_message(self, message: discord.Message, now_date_str: str):
        if self.lock:
            return

        guild = message.guild
        channel = message.channel
        user = message.author

        if guild is None or message.author.id == self.bot.user.id:
            return

        channel_config = self.settings.channels(guild.id).get(channel.id, None)
        if not channel_config:
            return

        acceptable, _, _ = await self.check_acceptable(message, message.content)
        if not acceptable:
            return

        max_points = channel_config['max_ppd']
        current_points = await self.get_current_channel_points(now_date_str, guild, channel, user)
        current_points = current_points or 0

        if current_points >= max_points:
            return

        server_point_cap = self.settings.server_point_cap(guild.id)
        current_server_points = await self.get_current_server_points(now_date_str, guild, user)
        current_server_points = current_server_points or 0

        if current_server_points >= server_point_cap:
            return

        message_cap = self.settings.message_cap(guild.id)
        incremental_points = max_points / message_cap
        new_points = current_points + incremental_points
        new_points = min(new_points, max_points)

        before_time = timeit.default_timer()
        await self.save_current_points(now_date_str, guild, channel, user, new_points)
        execution_time = timeit.default_timer() - before_time
        self.insert_timing.append(execution_time)

        return incremental_points

    async def get_current_channel_points(self, now_date_str: str, server: discord.Guild, channel: discord.TextChannel,
                                         user: discord.User):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(GET_NEWMESSAGE_POINTS_QUERY, now_date_str, server.id, channel.id, user.id)
                results = await cur.fetchone()
                return results.points if results else 0

    async def get_current_server_points(self, now_date_str: str, server: discord.Guild, user: discord.User):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(GET_NEWMESSAGE_SERVER_POINTS_QUERY, now_date_str, server.id, user.id)
                results = await cur.fetchone()
                return results.points if results else 0

    async def save_current_points(self, now_date_str: str, server: discord.Guild, channel: discord.TextChannel,
                                  user: discord.User, new_points: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(REPLACE_POINTS_QUERY, now_date_str, server.id, channel.id, user.id, new_points)

    async def queryAndPrint(self, ctx, server, query, values, max_rows=100, reverse=False, total=False):
        before_time = timeit.default_timer()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, *values)
                rows = await cur.fetchall()
                columns = [x[0] for x in cur.description]
        execution_time = timeit.default_timer() - before_time

        if reverse:
            rows.reverse()

        tbl = prettytable.PrettyTable(columns)
        tbl.hrules = prettytable.HEADER
        tbl.vrules = prettytable.NONE
        tbl.align = 'l'

        grand_total = 0

        for idx, row in enumerate(rows):
            if idx > max_rows:
                break

            table_row = list()
            for cidx, col in enumerate(columns):
                raw_value = row[cidx]
                value = str(raw_value)
                if col == 'timestamp':
                    # Assign a UTC timezone to the datetime
                    raw_value = raw_value.replace(tzinfo=pytz.utc)
                    # Change the UTC timezone to PT
                    raw_value = NA_TZ_OBJ.normalize(raw_value)
                    value = raw_value.strftime("%F %X")
                elif col == 'channel_id':
                    channel = server.get_channel(int(value)) if server else None
                    value = channel.name if channel else value
                elif col == 'user_id':
                    member = server.get_member(int(value)) if server else None
                    value = member.name if member else value
                elif col == 'server_id':
                    server_obj = self.bot.get_guild(int(value))
                    value = server_obj.name if server_obj else value
                elif cidx + 1 == len(columns):
                    grand_total += force_number(value)
                table_row.append(value)

            tbl.add_row(table_row)

        result_text = "{} results fetched in {}s\n{}".format(
            len(rows), round(execution_time, 2), tbl.get_string())

        if total:
            result_text += '\n\nTotal: {}'.format(grand_total)

        for p in pagify(result_text):
            await ctx.send(box(p))


def ensure_map(item, key, default_value):
    if key not in item:
        item[key] = default_value
    return item[key]


def now_date():
    return datetime.now(rpadutils.NA_TZ_OBJ).date().isoformat()


class SenioritySettings(CogSettings):
    def make_default_settings(self):
        config = {
            'servers': {}
        }
        return config

    def servers(self):
        return self.bot_settings['servers']

    def server(self, server_id: str):
        servers = self.servers()
        return ensure_map(servers, server_id, {})

    def config(self, server_id: str):
        server = self.server(server_id)
        config = ensure_map(server, 'config', {})
        ensure_map(config, 'announce_channel', '')
        ensure_map(config, 'auto_grant', False)
        ensure_map(config, 'message_cap', 20)
        ensure_map(config, 'server_point_cap', 5)
        ensure_map(config, 'grant_lookback', 90)
        ensure_map(config, 'remove_lookback', 90)
        return config

    def announce_channel(self, server_id: str):
        return self.config(server_id)['announce_channel']

    def auto_grant(self, server_id: str):
        return self.config(server_id)['auto_grant']

    def message_cap(self, server_id: str):
        return self.config(server_id)['message_cap']

    def server_point_cap(self, server_id: str):
        return self.config(server_id)['server_point_cap']

    def grant_lookback(self, server_id: str):
        return self.config(server_id)['grant_lookback']

    def remove_lookback(self, server_id: str):
        return self.config(server_id)['remove_lookback']

    def set_announce_channel(self, server_id: str, channel_id):
        self.config(server_id)['announce_channel'] = channel_id
        self.save_settings()

    def set_auto_grant(self, server_id: str, auto_grant: bool):
        self.config(server_id)['auto_grant'] = auto_grant
        self.save_settings()

    def set_message_cap(self, server_id, message_cap: int):
        self.config(server_id)['message_cap'] = message_cap
        self.save_settings()

    def set_server_point_cap(self, server_id, server_point_cap: int):
        self.config(server_id)['server_point_cap'] = server_point_cap
        self.save_settings()

    def set_grant_lookback(self, server_id: str, lookback: int):
        self.config(server_id)['grant_lookback'] = lookback
        self.save_settings()

    def set_remove_lookback(self, server_id: str, lookback: int):
        self.config(server_id)['remove_lookback'] = lookback
        self.save_settings()

    def roles(self, server_id):
        server = self.server(server_id)
        return ensure_map(server, 'roles', {})

    def set_role(self, server_id: str, role_id: str, remove_amount: int, warn_amount: int, grant_amount: int):
        roles = self.roles(server_id)
        if remove_amount == 0 and grant_amount == 0:
            roles.pop(role_id, None)
        elif remove_amount >= grant_amount:
            raise commands.UserFeedbackCheckFailure('remove_amount must be less than grant_amount')
        elif warn_amount >= grant_amount:
            raise commands.UserFeedbackCheckFailure('warn_amount must be less than grant_amount')
        elif remove_amount < 0 or warn_amount < 0 or grant_amount < 0:
            raise commands.UserFeedbackCheckFailure('role values must be >= 0')
        else:
            roles[role_id] = {
                'role_id': role_id,
                'remove_amount': remove_amount,
                'warn_amount': warn_amount,
                'grant_amount': grant_amount,
            }
        self.save_settings()

    def utterances(self, server_id: str):
        server = self.server(server_id)
        utterances = ensure_map(server, 'utterances', {})
        ensure_map(utterances, 'ignore_commands', True)
        ensure_map(utterances, 'ignore_emoji', True)
        ensure_map(utterances, 'ignore_mentions', True)
        ensure_map(utterances, 'ignore_room_codes', True)
        ensure_map(utterances, 'min_length', 30)
        ensure_map(utterances, 'min_words', 5)
        return utterances

    def ignore_commands(self, server_id: str):
        return self.utterances(server_id)['ignore_commands']

    def ignore_emoji(self, server_id: str):
        return self.utterances(server_id)['ignore_emoji']

    def ignore_mentions(self, server_id: str):
        return self.utterances(server_id)['ignore_mentions']

    def ignore_room_codes(self, server_id: str):
        return self.utterances(server_id)['ignore_room_codes']

    def min_length(self, server_id: str):
        return self.utterances(server_id)['min_length']

    def min_words(self, server_id: str):
        return self.utterances(server_id)['min_words']

    def set_ignore_commands(self, server_id: str, ignore: bool):
        self.utterances(server_id)['ignore_commands'] = ignore
        self.save_settings()

    def set_ignore_emoji(self, server_id: str, ignore: bool):
        self.utterances(server_id)['ignore_emoji'] = ignore
        self.save_settings()

    def set_ignore_mentions(self, server_id: str, ignore: bool):
        self.utterances(server_id)['ignore_mentions'] = ignore
        self.save_settings()

    def set_ignore_room_codes(self, server_id: str, ignore: bool):
        self.utterances(server_id)['ignore_room_codes'] = ignore
        self.save_settings()

    def set_min_length(self, server_id: str, min_length: int):
        self.utterances(server_id)['min_length'] = min_length
        self.save_settings()

    def set_min_words(self, server_id: str, min_words: int):
        self.utterances(server_id)['min_words'] = min_words
        self.save_settings()

    def blacklist(self, server_id: str):
        server = self.server(server_id)
        return ensure_map(server, 'blacklist', {})

    def add_blacklist(self, server_id: str, user_id: str, by_id: str, reason: str):
        blacklist = self.blacklist(server_id)
        blacklist[user_id] = {
            'user_id': user_id,
            'by_id': by_id,
            'ignore_date': now_date(),
            'reason': reason,
        }
        self.save_settings()

    def remove_blacklist(self, server_id: str, user_id: str):
        blacklist = self.blacklist(server_id)
        result = blacklist.pop(user_id, None)
        self.save_settings()
        return result

    def channels(self, server_id: str):
        server = self.server(server_id)
        return ensure_map(server, 'channels', {})

    def set_channel(self, server_id: str, channel_id: str, max_ppd: int):
        channels = self.channels(server_id)
        if max_ppd == 0:
            channels.pop(channel_id, None)
        else:
            channels[channel_id] = {
                'channel_id': channel_id,
                'max_ppd': max_ppd,
            }
        self.save_settings()


def force_number(s):
    try:
        return float(s)
    except ValueError:
        return 0
