import os
import sqlite3 as lite
import textwrap
import timeit
from collections import deque
from datetime import datetime, timedelta

import prettytable
import pytz
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import *

import rpadutils
from rpadutils import CogSettings

TIMESTAMP_FORMAT = '%Y-%m-%d %X'  # YYYY-MM-DD HH:MM:SS
PATH_LIST = ['data', 'sqlactivitylog']
PATH = os.path.join(*PATH_LIST)
JSON = os.path.join(*PATH_LIST, "settings.json")
DB = os.path.join(*PATH_LIST, "log.db")

ALL_COLUMNS = [
    ('timestamp', 'Time (PT)'),
    ('server_id', 'Server'),
    ('channel_id', 'Channel'),
    ('user_id', 'User'),
    ('msg_type', 'Type'),
    ('clean_content', 'Message'),
]

CREATE_TABLE = '''
CREATE TABLE IF NOT EXISTS messages(
  rowid INTEGER PRIMARY KEY ASC AUTOINCREMENT,
  timestamp TIMESTAMP NOT NULL,
  server_id STRING NOT NULL,
  channel_id STRING NOT NULL,
  user_id STRING NOT NULL,
  msg_type STRING NOT NULL,
  content STRING NOT NULL,
  clean_content STRING NOT NULL)
'''

CREATE_INDEX_1 = '''
CREATE INDEX IF NOT EXISTS idx_messages_server_id_channel_id_user_id_timestamp
ON messages(server_id, channel_id, user_id, timestamp)
'''

CREATE_INDEX_2 = '''
CREATE INDEX IF NOT EXISTS idx_messages_server_id_user_id_timestamp
ON messages(server_id, user_id, timestamp)
'''

CREATE_INDEX_3 = '''
CREATE INDEX IF NOT EXISTS idx_messages_server_id_clean_content
ON messages(server_id, clean_content)
'''

CREATE_INDEX_4 = '''
CREATE INDEX IF NOT EXISTS idx_messages_server_id_timestamp
ON messages(server_id, timestamp)
'''

CREATE_INDEX_5 = '''
CREATE INDEX IF NOT EXISTS idx_messages_server_id_channel_id_timestamp
ON messages(server_id, channel_id, timestamp)
'''

MAX_LOGS = 500

USER_QUERY = '''
SELECT * FROM (
    SELECT timestamp, channel_id, msg_type, clean_content
    FROM messages INDEXED BY idx_messages_server_id_user_id_timestamp
    WHERE server_id = :server_id
      AND user_id = :user_id
    ORDER BY timestamp DESC
    LIMIT :row_count
)
ORDER BY timestamp ASC
'''

CHANNEL_QUERY = '''
SELECT * FROM (
    SELECT timestamp, user_id, msg_type, clean_content
    FROM messages INDEXED BY idx_messages_server_id_channel_id_timestamp
    WHERE server_id = :server_id
      AND channel_id = :channel_id
      AND user_id <> :bot_id
    ORDER BY timestamp DESC
    LIMIT :row_count
)
ORDER BY timestamp ASC
'''

USER_CHANNEL_QUERY = '''
SELECT * FROM (
    SELECT timestamp, msg_type, clean_content
    FROM messages INDEXED BY idx_messages_server_id_channel_id_user_id_timestamp
    WHERE server_id = :server_id
      AND user_id = :user_id
      AND channel_id = :channel_id
    ORDER BY timestamp DESC
    LIMIT :row_count
)
ORDER BY timestamp ASC
'''

CONTENT_QUERY = '''
SELECT * FROM (
    SELECT timestamp, channel_id, user_id, msg_type, clean_content
    FROM messages INDEXED BY idx_messages_server_id_clean_content
    WHERE server_id = :server_id
      AND lower(clean_content) LIKE lower(:content_query)
      AND user_id <> :bot_id
    ORDER BY timestamp DESC
    LIMIT :row_count
)
ORDER BY timestamp ASC
'''

WHOSAYS_QUERY = '''
SELECT user_id, count(*)
FROM messages INDEXED BY idx_messages_server_id_clean_content
WHERE server_id = :server_id
  AND lower(clean_content) LIKE lower(:content_query)
  AND user_id <> :bot_id
  AND msg_type = 'NEW'
GROUP BY 1
ORDER BY 2 DESC
LIMIT :row_count
'''

DAILY_REPORT_QUERY = '''
SELECT DATE(timestamp) AS date, COUNT(DISTINCT user_id) AS distinct_users, count(*) AS total_messages
FROM messages INDEXED BY idx_messages_server_id_timestamp
WHERE server_id = :server_id
  AND timestamp > :start_timestamp
GROUP BY date
ORDER BY date DESC
LIMIT :row_count
'''

PERIOD_REPORT_QUERY = '''
SELECT COUNT(DISTINCT user_id) AS distinct_users, count(*) AS total_messages
FROM messages INDEXED BY idx_messages_server_id_timestamp
WHERE server_id = :server_id
  AND timestamp between :start_timestamp and :end_timestamp
'''

CHANNEL_REPORT_QUERY = '''
SELECT user_id, count(*) AS total_messages
FROM messages INDEXED BY idx_messages_server_id_channel_id_timestamp
WHERE server_id = :server_id
  AND channel_id = :channel_id
  AND timestamp between :start_timestamp and :end_timestamp
GROUP BY 1
ORDER BY 2 DESC
LIMIT :row_count
'''

USER_REPORT_QUERY = '''
SELECT channel_id, count(*) AS total_messages
FROM messages INDEXED BY idx_messages_server_id_user_id_timestamp
WHERE server_id = :server_id
  AND user_id = :user_id
  AND timestamp between :start_timestamp and :end_timestamp
GROUP BY 1
ORDER BY 2 DESC
LIMIT :row_count
'''

SENIORITY_BACKFILL_QUERY = '''
SELECT user_id, content
FROM messages INDEXED BY idx_messages_server_id_channel_id_timestamp
WHERE server_id = :server_id
  AND channel_id = :channel_id
  AND timestamp between :start_timestamp and :end_timestamp
'''


class SqlActivityLogger(commands.Cog):
    """Log activity seen by bot"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.settings = SQLSettings("sqlactivitylog")
        self.lock = False
        self.con = lite.connect(DB, detect_types=lite.PARSE_DECLTYPES)
        self.con.row_factory = lite.Row
        self.con.execute(CREATE_TABLE)
        self.con.execute(CREATE_INDEX_1)
        self.con.execute(CREATE_INDEX_2)
        self.con.execute(CREATE_INDEX_3)
        self.con.execute(CREATE_INDEX_4)
        self.con.execute(CREATE_INDEX_5)
        self.insert_timing = deque(maxlen=1000)

    def __unload(self):
        self.lock = True
        self.con.close()

    @commands.command()
    @checks.is_owner()
    async def rawquery(self, ctx, *, query: str):
        await self.queryAndPrint(ctx, ctx.guild, query, {}, {})

    @commands.command()
    @checks.is_owner()
    async def inserttiming(self, ctx):
        size = len(self.insert_timing)
        avg_time = round(sum(self.insert_timing) / size, 4)
        max_time = round(max(self.insert_timing), 4)
        min_time = round(min(self.insert_timing), 4)
        await ctx.send(inline('{} inserts, min={} max={} avg={}'.format(size, min_time, max_time, avg_time)))

    @commands.command()
    @checks.is_owner()
    async def togglelock(self, ctx):
        self.lock = not self.lock
        await ctx.send(inline('Locked is now {}'.format(self.lock)))

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def exlog(self, context):
        """Extra log querying tools.

        Uses the bot's local SQL message storage to retrieve messages
        seen in the current server since the cog was installed.
        """

    @exlog.command()
    @commands.guild_only()
    async def user(self, ctx, user: discord.User, count=10):
        """exlog user tactical_retreat 100

        List of messages for a user across all channels.
        Count is optional, with a low default and a maximum value.
        """
        count = min(count, MAX_LOGS)
        server = ctx.guild
        values = {
            'server_id': server.id,
            'row_count': count,
            'user_id': user.id,
        }
        column_data = [
            ('timestamp', 'Time (PT)'),
            ('channel_id', 'Channel'),
            ('msg_type', 'Type'),
            ('clean_content', 'Message'),
        ]

        await self.queryAndPrint(ctx, server, USER_QUERY, values, column_data)

    @exlog.command()
    @commands.guild_only()
    async def channel(self, ctx, channel: discord.TextChannel, count=10):
        """exlog channel #general_chat 100

        List of messages in a given channel.
        Count is optional, with a low default and a maximum value.
        The bot is excluded from results.
        """
        count = min(count, MAX_LOGS)
        server = ctx.guild
        values = {
            'server_id': server.id,
            'bot_id': self.bot.user.id,
            'row_count': count,
            'channel_id': channel.id,
        }
        column_data = [
            ('timestamp', 'Time (PT)'),
            ('user_id', 'User'),
            ('msg_type', 'Type'),
            ('clean_content', 'Message'),
        ]

        await self.queryAndPrint(ctx, server, CHANNEL_QUERY, values, column_data)

    @exlog.command()
    @commands.guild_only()
    async def userchannel(self, ctx, user: discord.User, channel: discord.TextChannel, count=10):
        """exlog userchannel tactical_retreat #general_chat 100

        List of messages from a user in a given channel.
        Count is optional, with a low default and a maximum value.
        """
        count = min(count, MAX_LOGS)
        server = ctx.guild
        values = {
            'server_id': server.id,
            'row_count': count,
            'channel_id': channel.id,
            'user_id': user.id,
        }
        column_data = [
            ('timestamp', 'Time (PT)'),
            ('msg_type', 'Type'),
            ('clean_content', 'Message'),
        ]

        await self.queryAndPrint(ctx, server, USER_CHANNEL_QUERY, values, column_data)

    @exlog.command()
    @commands.guild_only()
    async def query(self, ctx, query, count=10):
        """exlog query "4 whale" 100

        Case-insensitive search of messages from every user/channel.
        Put the query in quotes if it is more than one word.
        Count is optional, with a low default and a maximum value.
        The bot is excluded from results.
        """
        if query[0] in ('%', '_'):
            await ctx.send('`You cannot start this query with a wildcard`')
            return

        count = min(count, MAX_LOGS)
        server = ctx.guild
        values = {
            'server_id': server.id,
            'bot_id': self.bot.user.id,
            'row_count': count,
            'content_query': query,
        }
        column_data = [
            ('timestamp', 'Time (PT)'),
            ('channel_id', 'Channel'),
            ('user_id', 'User'),
            ('msg_type', 'Type'),
            ('clean_content', 'Message'),
        ]

        await self.queryAndPrint(ctx, server, CONTENT_QUERY, values, column_data)

    @exlog.command()
    @commands.guild_only()
    async def whosays(self, ctx, query, count=10):
        """exlog whosays "%:thinking:%" 10

        Case-insensitive search of messages from every user/channel, grouped by user.
        Put the query in quotes if it is more than one word.
        Count is optional, with a low default and a maximum value.
        The bot is excluded from results.
        """
        if query[0] in ('%', '_'):
            await ctx.send('`You cannot start this query with a wildcard`')
            return

        count = min(count, MAX_LOGS)
        server = ctx.guild
        values = {
            'server_id': server.id,
            'bot_id': self.bot.user.id,
            'row_count': count,
            'content_query': query,
        }
        column_data = [
            ('user_id', 'User'),
        ]

        await self.queryAndPrint(ctx, server, WHOSAYS_QUERY, values, column_data)

    @exlog.command()
    @commands.guild_only()
    async def dailyreport(self, ctx, count=10):
        """exlog dailyreport 10

        Prints a report on user activity for the specified day count.
        """
        count = min(count, 30)
        start_date = datetime.today() - timedelta(days=(count + 1))
        server = ctx.guild
        values = {
            'server_id': server.id,
            'row_count': count,
            'start_timestamp': start_date,
        }
        column_data = []

        await self.queryAndPrint(ctx, server, DAILY_REPORT_QUERY, values, column_data)

    @exlog.command()
    @commands.guild_only()
    async def periodreport(self, ctx, start_date, end_date):
        """exlog periodreport 2017-01-01 2017-01-10

        Prints a report on user activity for the specified time period.
        Be careful how you specify your dates, must match the YYYY-MM-DD format
        described above.
        Start date is inclusive, end date is exclusive.
        """
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

        start_date = start_date.replace(tzinfo=pytz.utc)
        end_date = end_date.replace(tzinfo=pytz.utc)

        server = ctx.guild
        values = {
            'server_id': server.id,
            'start_timestamp': start_date,
            'end_timestamp': end_date,
        }
        column_data = []

        await self.queryAndPrint(ctx, server, PERIOD_REPORT_QUERY, values, column_data)

    @exlog.command()
    @commands.guild_only()
    async def channelreport(self, ctx, channel: discord.TextChannel, start_date: str, end_date: str, count=10):
        """exlog channelreport #general_chat 2017-01-01 2017-01-10

        Prints a report on user activity for the specified time period in a channel.
        Be careful how you specify your dates, must match the YYYY-MM-DD format
        described above.
        Start date is inclusive, end date is exclusive.
        """
        count = min(count, 30)
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

        start_date = start_date.replace(tzinfo=pytz.utc)
        end_date = end_date.replace(tzinfo=pytz.utc)

        server = ctx.guild
        values = {
            'server_id': server.id,
            'channel_id': channel.id,
            'start_timestamp': start_date,
            'end_timestamp': end_date,
            'row_count': count,
        }
        column_data = []

        await self.queryAndPrint(ctx, server, CHANNEL_REPORT_QUERY, values, column_data)

    @exlog.command()
    @commands.guild_only()
    async def userreport(self, ctx, user: discord.User, start_date: str, end_date: str, count=10):
        """exlog userreport tactical_retreat 2017-01-01 2017-01-10

        Prints a report on channel activity in the specified time period for a user.
        Be careful how you specify your dates, must match the YYYY-MM-DD format
        described above.
        Start date is inclusive, end date is exclusive.
        """
        count = min(count, 30)
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

        start_date = start_date.replace(tzinfo=pytz.utc)
        end_date = end_date.replace(tzinfo=pytz.utc)

        server = ctx.guild
        values = {
            'server_id': server.id,
            'user_id': user.id,
            'start_timestamp': start_date,
            'end_timestamp': end_date,
            'row_count': count,
        }
        column_data = []

        await self.queryAndPrint(ctx, server, USER_REPORT_QUERY, values, column_data)

    async def queryAndPrint(self, ctx, server, query, values, column_data, max_rows=MAX_LOGS * 2):
        before_time = timeit.default_timer()
        cursor = self.con.execute(query, values)
        rows = cursor.fetchall()
        execution_time = timeit.default_timer() - before_time

        if len(column_data) == 0:
            column_data = ALL_COLUMNS

        results_columns = [d[0] for d in cursor.description]
        column_data = [r for r in column_data if r[0] in results_columns]
        for missing_col in [col for col in results_columns if col not in [c[0] for c in column_data]]:
            column_data.append((missing_col, missing_col))

        column_names = [c[0] for c in column_data]
        column_headers = [c[1] for c in column_data]

        tbl = prettytable.PrettyTable(column_headers)
        tbl.hrules = prettytable.HEADER
        tbl.vrules = prettytable.NONE
        tbl.align = 'l'

        for idx, row in enumerate(rows):
            if idx > max_rows:
                break

            table_row = list()
            for col in column_names:
                if col not in row.keys():
                    table_row.append('')
                    continue
                raw_value = row[col]
                value = str(raw_value)
                if col == 'timestamp':
                    # Assign a UTC timezone to the datetime
                    raw_value = raw_value.replace(tzinfo=pytz.utc)
                    # Change the UTC timezone to PT
                    raw_value = rpadutils.NA_TZ_OBJ.normalize(raw_value)
                    value = raw_value.strftime("%F %X")
                if col == 'channel_id':
                    channel = server.get_channel(value) if server else None
                    value = channel.name if channel else value
                if col == 'user_id':
                    member = server.get_member(value) if server else None
                    value = member.name if member else value
                if col == 'server_id':
                    server_obj = self.bot.get_server(value)
                    value = server_obj.name if server_obj else value
                if col == 'clean_content':
                    value = value.replace('```', '~~~')
                    value = value.replace('`', '\`')
                    value = '\n'.join(textwrap.wrap(value, 60))
                table_row.append(value)

            tbl.add_row(table_row)

        result_text = "{} results fetched in {}s\n{}".format(
            len(rows), round(execution_time, 2), tbl.get_string())
        for p in pagify(result_text):
            await ctx.send(box(p))

    def save_json(self):
        self.settings.save_settings()

    async def on_message(self, message):
        self.log('NEW', message, message.created_at)

    async def on_message_edit(self, before, after):
        self.log('EDIT', after, after.edited_at)

    async def on_message_delete(self, message):
        self.log('DELETE', message, datetime.utcnow())

    def log(self, msg_type, message, timestamp):
        if self.lock:
            return

        if message.author.id == self.bot.user.id:
            return

        stmt = '''
          INSERT INTO messages(timestamp, server_id, channel_id, user_id, msg_type, content, clean_content)
          VALUES(:timestamp, :server_id, :channel_id, :user_id, :msg_type, :content, :clean_content)
        '''
        timestamp = timestamp or datetime.utcnow()
        server_id = message.guild.id if message.guild else -1
        channel_id = message.channel.id if message.channel else -1

        msg_content = message.content
        msg_clean_content = message.clean_content
        if message.attachments:
            extra_txt = '\nattachments: ' + str(message.attachments)
            msg_content = (msg_content + extra_txt).strip()
            msg_clean_content = (msg_clean_content + extra_txt).strip()

        if message.embeds:
            extra_txt = '\nembeds: ' + str(message.embeds)
            msg_content = (msg_content + extra_txt).strip()
            msg_clean_content = (msg_clean_content + extra_txt).strip()

        values = {
            'timestamp': timestamp,
            'server_id': server_id,
            'channel_id': channel_id,
            'user_id': message.author.id,
            'msg_type': msg_type,
            'content': msg_content,
            'clean_content': msg_clean_content,
        }

        before_time = timeit.default_timer()
        self.con.execute(stmt, values)
        self.con.commit()
        execution_time = timeit.default_timer() - before_time
        self.insert_timing.append(execution_time)

    def get_server_channel_date_msgs(self, server_id, channel_id, start_date_str):
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        start_date = start_date.replace(tzinfo=rpadutils.NA_TZ_OBJ)
        end_date = start_date + timedelta(days=1)

        values = {
            'server_id': server_id,
            'channel_id': channel_id,
            'start_timestamp': start_date,
            'end_timestamp': end_date,
        }

        cursor = self.con.execute(SENIORITY_BACKFILL_QUERY, values)
        rows = cursor.fetchall()
        return [(str(r['user_id']), str(r['content'])) for r in rows]


class SQLSettings(CogSettings):
    def make_default_settings(self):
        config = {}
        return config
