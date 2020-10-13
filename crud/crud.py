import asyncio
import csv
import discord
import io
import json
import logging
import pymysql
from datetime import datetime
from redbot.core import checks, commands, Config, errors
from redbot.core.utils.chat_formatting import box, inline, pagify
from tsutils import auth_check, confirm_message

logger = logging.getLogger('red.padbot-cogs.crud')

TokenConverter = commands.get_dict_converter(delims=[" ", ",", ";"])

SERIES_KEYS = {
    "name_en": 'Untranslated',
    "name_ja": 'Untranslated',
    "name_ko": 'Untranslated',
}

class Crud(commands.Cog):
    """PadGuide CRUD"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=3270)
        self.config.register_global(config_file=None)

        GADMIN_COG = self.bot.get_cog("GlobalAdmin")
        if GADMIN_COG:
            GADMIN_COG.register_perm("crud")
        else:
            raise errors.CogLoadError("Global Administration cog must be loaded.")

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    async def get_cursor(self):
        with open(await self.config.config_file(), 'r') as db_config:
            return self.connect(json.load(db_config)).cursor()

    def connect(self, db_config):
        return pymysql.connect(host=db_config['host'],
                               user=db_config['user'],
                               password=db_config['password'],
                               db=db_config['db'],
                               charset=db_config['charset'],
                               cursorclass=pymysql.cursors.DictCursor,
                               autocommit=True)

    @commands.group(aliases=['hera-ur'])
    @auth_check('crud')
    async def crud(self, ctx):
        """PadGuide database CRUD."""

    @crud.command()
    async def searchdungeon(self, ctx, *, search_text):
        """Search"""
        search_text = '%{}%'.format(search_text)
        with await self.get_cursor() as cursor:
            sql = ('select dungeon_id, name_en, name_ja, visible from dungeons'
                   ' where lower(name_en) like %s or lower(name_ja) like %s'
                   ' order by dungeon_id desc limit 20')
            cursor.execute(sql, [search_text, search_text])
            results = list(cursor.fetchall())
            msg = 'Results\n' + json.dumps(results, indent=2, ensure_ascii=False)
            await ctx.send(inline(sql))
            for page in pagify(msg):
                await ctx.send(box(page))

    @crud.group()
    async def series(self, ctx):
        """Series"""

    @series.command(name="search")
    async def series_search(self, ctx, *, search_text):
        """Search"""
        search_text = '%{}%'.format(search_text)
        with await self.get_cursor() as cursor:
            sql = ('select series_id, name_en, name_ja from series'
                   ' where lower(name_en) like %s or lower(name_ja) like %s'
                   ' order by series_id desc limit 20')
            cursor.execute(sql, [search_text, search_text])
            results = list(cursor.fetchall())
            msg = 'Results\n' + json.dumps(results, indent=2, ensure_ascii=False)
            await ctx.send(inline(sql))
            for page in pagify(msg):
                await ctx.send(box(page))

    @series.command(name="add")
    async def series_add(self, ctx, *, elements: TokenConverter):
        """Add"""
        if not all(x in SERIES_KEYS for x in elements):
            await ctx.send("Invalid key.  Valid keys are: `{}`".format("` `".join(SERIES_KEYS)))
            return

        EXTRAS = {}
        with await self.get_cursor() as cursor:
            cursor.execute("SELECT MAX(series_id) FROM series")
            max_val = cursor.fetchall()[0]['MAX(series_id)']
            EXTRAS['series_id'] = max_val + 1
        EXTRAS['tstamp'] = int(datetime.now().timestamp())
        elements = {**SERIES_KEYS, **EXTRAS, **elements}

        key_infix = ", ".join(elements.keys())
        value_infix = ", ".join("%s" for v in elements.values())
        with await self.get_cursor() as cursor:
            sql = ('INSERT INTO series ({})'
                   ' VALUES ({})').format(key_infix, value_infix)
            affected = cursor.execute(sql, (*elements.values(),))
            await ctx.send(inline(cursor._executed))
            await ctx.send("{} row(s) added.".format(affected))

    @series.command(name="edit")
    async def series_edit(self, ctx, series_id: int, *, elements: TokenConverter):
        """Edit"""
        if not all(x in SERIES_KEYS for x in elements):
            await ctx.send("Invalid key.  Valid keys are: `{}`".format("` `".join(SERIES_KEYS)))
            return

        replacement_infix = ", ".join(["{} = %s".format(k) for k in elements.keys()])
        with await self.get_cursor() as cursor:
            sql = ('UPDATE series'
                   ' SET {}'
                   ' WHERE series_id = %s').format(replacement_infix)
            affected = cursor.execute(sql, (*elements.values(),) + (series_id,))
            await ctx.send(inline(cursor._executed))
            await ctx.send("{} row(s) changed.".format(affected))

    @series.command(name="delete")
    async def series_delete(self, ctx, series_id: int):
        """Delete"""
        with await self.get_cursor() as cursor:
            sql = ('DELETE FROM series'
                   ' WHERE series_id = %s')
            affected = cursor.execute(sql, series_id)
            await ctx.send(inline(cursor._executed))
            await ctx.send("{} row(s) deleted.".format(affected))

    @crud.command()
    async def editmonsname(self, ctx, monster_id: int, *, name):
        """Change a monster's name_en_override"""
        if name.lower() in ["none", "null"]:
            name = None
        with await self.get_cursor() as cursor:
            cursor.execute("SELECT name_en_override FROM monsters WHERE monster_id = %s", (monster_id,))
            old_val = cursor.fetchall()
            if not old_val:
                await ctx.send("There is no monster with id: {}".format(monster_id))
                return
            old_val = old_val[0]['name_en_override']
            if not await confirm_message(ctx, ("Are you sure you want to change monster #{}'s"
                                               " english override from `{}` to `{}`?").format(monster_id,
                                                      old_val, name)):
                return

            sql = ('UPDATE monsters'
                   ' SET name_en_override = %s'
                   ' WHERE monster_id = %s')
            affected = cursor.execute(sql, (name, monster_id))
            await ctx.send("Changed `{}` to `{}` via:".format(old_val, name))
            await ctx.send(inline(cursor._executed))
            await ctx.send("{} row(s) changed.".format(affected))

    @crud.command()
    async def editmonsseries(self, ctx, monster_id: int, *, series_id: int):
        """Change a monster's series_id"""
        with await self.get_cursor() as cursor:
            cursor.execute("SELECT series_id FROM monsters WHERE monster_id = %s", (monster_id,))
            old_val = cursor.fetchall()
            if not old_val:
                await ctx.send("There is no monster with id: {}".format(monster_id))
                return
            old_val = old_val[0]['series_id']
            if not await confirm_message(ctx, ("Are you sure you want to change monster #{}'s"
                                               " series_id from `{}` to `{}`?").format(monster_id,
                                                     old_val, series_id)):
                return

            sql = ('UPDATE monsters'
                   ' SET series_id = %s'
                   ' WHERE monster_id = %s')
            affected = cursor.execute(sql, (series_id, monster_id))
            await ctx.send("Changed `{}` to `{}` via:\n".format(old_val, series_id, inline(cursor._executed)))
            await ctx.send("{} row(s) changed.".format(affected))

    @crud.command()
    @checks.is_owner()
    async def setconfig(self, ctx, path):
        await self.config.config_file.set(path)
        await ctx.tick()
