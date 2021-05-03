import json
import logging
import os
from datetime import datetime
from io import BytesIO

import aiofiles
import discord
import pymysql
from redbot.core import checks, commands, Config, errors
from redbot.core.utils.chat_formatting import box, inline, pagify
from tsutils import auth_check, confirm_message

logger = logging.getLogger('red.padbot-cogs.crud')

SERIES_KEYS = {
    "name_en": 'Untranslated',
    "name_ja": 'Untranslated',
    "name_ko": 'Untranslated',
    "series_type": None,
}

AWOKEN_SKILL_KEYS = {
    "awoken_skill_id": -1,
    "name_en": 'Untranslated',
    "name_ja": 'Untranslated',
    "name_ko": 'Untranslated',
    "desc_en": 'Untranslated',
    "desc_ja": 'Untranslated',
    "desc_ko": 'Untranslated',
}

SERIES_TYPES = [
    "regular",
    "event",
    "seasonal",
    "ghcollab",
    "collab",
    "lowpriority",
]


async def check_crud_channel(ctx):
    chan = await ctx.bot.get_cog("Crud").config.chan()
    return chan is None or chan == ctx.channel.id or ctx.author.id in ctx.bot.owner_ids


class Crud(commands.Cog):
    """PadGuide CRUD"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=3270)
        self.config.register_global(config_file=None, pipeline_base=None, chan=None)

        GADMIN_COG = self.bot.get_cog("GlobalAdmin")
        if GADMIN_COG:
            GADMIN_COG.register_perm("crud")
        else:
            raise errors.CogLoadError("Global Administration cog must be loaded.  Make sure it's "
                                      "installed from misc-cogs and load it via `^load globaladmin`")

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
        async with aiofiles.open(await self.config.config_file(), 'r') as db_config:
            return self.connect(json.loads(await db_config.read())).cursor()

    def connect(self, db_config):
        return pymysql.connect(host=db_config['host'],
                               user=db_config['user'],
                               password=db_config['password'],
                               db=db_config['db'],
                               charset=db_config['charset'],
                               cursorclass=pymysql.cursors.DictCursor,
                               autocommit=True)

    async def execute_write(self, ctx, sql, replacements):
        with await self.get_cursor() as cursor:
            affected = cursor.execute(sql, replacements)
            await ctx.send(inline(cursor._executed))
            await ctx.send("{} row(s) affected.".format(affected))

    async def execute_read(self, ctx, sql, replacements):
        with await self.get_cursor() as cursor:
            cursor.execute(sql, replacements)
            results = list(cursor.fetchall())
            msg = 'Results\n' + json.dumps(results, indent=2, ensure_ascii=False, sort_keys=True)
            await ctx.send(inline(cursor._executed))
            for page in pagify(msg):
                await ctx.send(box(page))

    @commands.group()
    @auth_check('crud')
    @commands.check(check_crud_channel)
    async def crud(self, ctx):
        """PadGuide database CRUD."""

    @crud.command()
    async def editmonsname(self, ctx, monster_id: int, *, name):
        """Change a monster's name_en_override

        To remove a name override, set the name to None, NULL, or ""
        """
        if name.startswith('"') and name.endswith('"') and name.count('"') <= 2:
            name = name[1:-1]

        if name.lower() in ["none", "null", ""]:
            name = None
        with await self.get_cursor() as cursor:
            cursor.execute("SELECT name_en_override FROM monsters WHERE monster_id = %s", (monster_id,))
            old_val = cursor.fetchall()

        if not old_val:
            await ctx.send("There is no monster with id: {}".format(monster_id))
            return
        old_val = old_val[0]['name_en_override']
        if not await confirm_message(ctx, ("Are you sure you want to change monster #{}'s"
                                           " english override from `{}` to `{}`?"
                                           "").format(monster_id, old_val, name)):
            return

        sql = ('UPDATE monsters'
               ' SET name_en_override = %s'
               ' WHERE monster_id = %s')
        await self.execute_write(ctx, sql, (name, monster_id))

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
                                           " series id from `{}` to `{}`?"
                                           "").format(monster_id, old_val, series_id)):
            return

        sql = ('UPDATE monsters'
               ' SET series_id = %s'
               ' WHERE monster_id = %s')
        await self.execute_write(ctx, sql, (series_id, monster_id))

    @crud.command()
    async def searchdungeon(self, ctx, *, search_text):
        """Search for a dungeon via its jp or na name"""
        search_text = '%{}%'.format(search_text).lower()
        sql = ('SELECT dungeon_id, name_en, name_ja, visible FROM dungeons'
               ' WHERE lower(name_en) LIKE %s OR lower(name_ja) LIKE %s'
               ' ORDER BY dungeon_id DESC LIMIT 20')
        await self.execute_read(ctx, sql, [search_text, search_text])

    @crud.group()
    async def series(self, ctx):
        """Series related commands"""

    @series.command(name="search")
    async def series_search(self, ctx, *, search_text):
        """Search for a series via its jp or na name"""
        search_text = '%{}%'.format(search_text).lower()
        sql = ('SELECT series_id, name_en, name_ja, name_ko FROM series'
               ' WHERE lower(name_en) LIKE %s OR lower(name_ja) LIKE %s'
               ' ORDER BY series_id DESC LIMIT 20')
        await self.execute_read(ctx, sql, [search_text, search_text])

    @series.command(name="add")
    async def series_add(self, ctx, *elements):
        """Add a new series.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `series_type`

        Example Usage:
        [p]crud series add key1 "Value1" key2 "Value2"
        """
        if len(elements) % 2 != 0:
            await ctx.send_help()
            return
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in SERIES_KEYS for x in elements)):
            await ctx.send_help()
            return

        if "series_type" in elements and elements['series_type'] not in SERIES_TYPES:
            await ctx.send("`series_type` must be one of: " + ", ".join(SERIES_TYPES))
            return

        EXTRAS = {}
        with await self.get_cursor() as cursor:
            cursor.execute("SELECT MAX(series_id) AS max_id FROM series")
            max_val = cursor.fetchall()[0]['max_id']
            EXTRAS['series_id'] = max_val + 1
        EXTRAS['tstamp'] = int(datetime.now().timestamp())
        elements = {**SERIES_KEYS, **EXTRAS, **elements}

        key_infix = ", ".join(elements.keys())
        value_infix = ", ".join("%s" for v in elements.values())
        sql = ('INSERT INTO series ({})'
               ' VALUES ({})').format(key_infix, value_infix)

        await self.execute_write(ctx, sql, (*elements.values(),))

        fn = os.path.join(await self.config.pipeline_base(), 'etl/pad/storage_processor/series.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        j.append({
            'name_ja': elements['name_ja'],
            'name_en': elements['name_en'],
            'name_ko': elements['name_ko'],
            'series_id': elements['series_id'],
            'series_type': elements['series_type']
        })
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))

    @series.command(name="edit")
    async def series_edit(self, ctx, series_id: int, *elements):
        """Edit an existing series.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `series_type`

        Example Usage:
        [p]crud series edit 100 key1 "Value1" key2 "Value2"
        """
        if len(elements) % 2 != 0:
            await ctx.send_help()
            return
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in SERIES_KEYS for x in elements)):
            await ctx.send_help()
            return

        if "series_type" in elements and elements['series_type'] not in SERIES_TYPES:
            await ctx.send("`series_type` must be one of: " + ", ".join(SERIES_TYPES))
            return

        replacement_infix = ", ".join(["{} = %s".format(k) for k in elements.keys()])
        sql = ('UPDATE series'
               ' SET {}'
               ' WHERE series_id = %s').format(replacement_infix)

        await self.execute_write(ctx, sql, (*elements.values(), series_id))

        fn = os.path.join(await self.config.pipeline_base(), 'etl/pad/storage_processor/series.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        for e in j:
            if e['series_id'] == series_id:
                e.update(elements)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))

    @series.command(name="delete")
    @checks.is_owner()
    async def series_delete(self, ctx, series_id: int):
        """Delete an existing series"""
        sql = ('DELETE FROM series'
               ' WHERE series_id = %s')

        await self.execute_write(ctx, sql, series_id)

        fn = os.path.join(await self.config.pipeline_base(), 'etl/pad/storage_processor/series.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        for e in j[:]:
            if e['series_id'] == series_id:
                j.remove(e)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))

    @crud.group(aliases=["awos"])
    async def awokenskill(self, ctx):
        """Awoken skill related commands"""

    @awokenskill.command(name="search")
    async def awokenskill_search(self, ctx, *, search_text):
        """Search for a awoken skill via its jp or na name"""
        search_text = '%{}%'.format(search_text).lower()
        sql = ('SELECT awoken_skill_id, name_en, name_ja, name_ko, desc_en,'
               ' desc_ja, desc_ko FROM awoken_skills'
               ' WHERE lower(name_en) LIKE %s OR lower(name_ja) LIKE %s'
               ' ORDER BY awoken_skill_id DESC LIMIT 20')
        await self.execute_read(ctx, sql, [search_text, search_text])

    @awokenskill.command(name="add")
    @checks.is_owner()
    async def awokenskill_add(self, ctx, *elements):
        """Add a new awoken skill.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `desc_en`, `desc_ko`, `desc_ja`

        Example Usage:
        [p]crud awokenskill add key1 "Value1" key2 "Value2"
        """
        if len(elements) % 2 != 0:
            await ctx.send_help()
            return
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in AWOKEN_SKILL_KEYS for x in elements)):
            await ctx.send_help()
            return

        if "awoken_skill_id" not in elements or not elements["awoken_skill_id"].isdigit():
            await ctx.send("You must supply an numeric `awoken_skill_id` when adding a new awoken skill.")
            return
        elements["awoken_skill_id"] = int(elements["awoken_skill_id"])

        EXTRAS = {
            'adj_hp': 0,
            'adj_atk': 0,
            'adj_rcv': 0,
            'tstamp': int(datetime.now().timestamp())
        }
        elements = {**AWOKEN_SKILL_KEYS, **EXTRAS, **elements}

        key_infix = ", ".join(elements.keys())
        value_infix = ", ".join("%s" for v in elements.values())
        sql = ('INSERT INTO awoken_skills ({})'
               ' VALUES ({})').format(key_infix, value_infix)

        await self.execute_write(ctx, sql, (*elements.values(),))

        fn = os.path.join(await self.config.pipeline_base(), 'etl/pad/storage_processor/awoken_skill.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        j.append({
            "adj_atk": 0,
            "adj_hp": 0,
            "adj_rcv": 0,
            "desc_ja": elements['desc_ja'],
            "desc_ja_official": "Unknown Official Text",
            "desc_ko": elements['desc_ko'],
            "desc_ko_official": "Unknown Official Text",
            "desc_en": elements['desc_en'],
            "desc_en_official": "Unknown Official Text",
            'name_ja': elements['name_ja'],
            "name_ja_official": "Unknown Official Name",
            'name_en': elements['name_en'],
            "name_ko_official": "Unknown Official Name",
            'name_ko': elements['name_ko'],
            "name_en_official": "Unknown Official Name",
            "pad_awakening_id": elements['awoken_skill_id'],
        })
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))

    @awokenskill.command(name="edit")
    async def awokenskill_edit(self, ctx, awoken_skill, *elements):
        """Edit an existing awoken skill.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `desc_en`, `desc_ko`, `desc_ja`

        Example Usage:
        [p]crud awokenskill edit 100 key1 "Value1" key2 "Value2"
        [p]crud awokenskill edit misc_comboboost key1 "Value1" key2 "Value2"
        """
        pdicog = self.bot.get_cog("PadInfo")
        emoji_to_awid = getattr(pdicog, 'awoken_emoji_names', {})

        if awoken_skill in emoji_to_awid:
            awoken_skill_id = emoji_to_awid[awoken_skill]
        elif awoken_skill.isdigit():
            awoken_skill_id = int(awoken_skill)
        else:
            await ctx.send("Invalid awoken skill.")
            return

        awoken_skill_id = int(awoken_skill_id)

        if len(elements) % 2 != 0:
            await ctx.send_help()
            return
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in AWOKEN_SKILL_KEYS for x in elements)):
            await ctx.send_help()
            return

        if 'awoken_skill_id' in elements:
            await ctx.send("`awoken_skill_id` is not a supported key for editing.")
            return

        replacement_infix = ", ".join(["{} = %s".format(k) for k in elements.keys()])
        sql = ('UPDATE awoken_skills'
               ' SET {}'
               ' WHERE awoken_skill_id = %s').format(replacement_infix)

        await self.execute_write(ctx, sql, (*elements.values(), awoken_skill_id))

        fn = os.path.join(await self.config.pipeline_base(), 'etl/pad/storage_processor/awoken_skill.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())

        for e in j:
            if e['pad_awakening_id'] == awoken_skill_id:
                e.update(elements)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))

    @awokenskill.command(name="delete")
    @checks.is_owner()
    async def awokenskill_delete(self, ctx, awoken_skill_id: int):
        """Delete an existing awoken skill"""
        sql = ('DELETE FROM awoken_skills'
               ' WHERE awoken_skill_id = %s')

        await self.execute_write(ctx, sql, awoken_skill_id)

        fn = os.path.join(await self.config.pipeline_base(), 'etl/pad/storage_processor/awoken_skill.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        for e in j[:]:
            if e['pad_awakening_id'] == awoken_skill_id:
                j.remove(e)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))

    @crud.command()
    @checks.is_owner()
    async def setconfig(self, ctx, path):
        await self.config.config_file.set(path)
        await ctx.tick()

    @crud.command()
    @checks.is_owner()
    async def pipeline_base(self, ctx, path):
        await self.config.pipeline_base.set(path)
        await ctx.tick()

    @crud.command()
    @checks.is_owner()
    async def setchan(self, ctx, channel: discord.TextChannel):
        await self.config.chan.set(channel.id)
        await ctx.tick()

    @crud.command()
    @checks.is_owner()
    async def rmchan(self, ctx):
        await self.config.chan.set(None)
        await ctx.tick()
