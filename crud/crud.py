import json
import logging
import os
import re
from datetime import datetime
from io import BytesIO
from typing import Any, TYPE_CHECKING

import aiofiles
import aiomysql
import discord
import pygit2
from redbot.core import Config, checks, commands, errors
from redbot.core.utils.chat_formatting import box, inline, pagify
from tsutils.cogs.globaladmin import auth_check
from tsutils.tsubaki.monster_header import MonsterHeader
from tsutils.user_interaction import get_user_confirmation, send_cancellation_message

from crud.editseries import EditSeries

if TYPE_CHECKING:
    from dbcog import DBCog

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


class Crud(commands.Cog, EditSeries):
    """PadGuide CRUD"""

    json_folder = 'etl/pad/storage_processor/'

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=3270)
        self.config.register_global(config_file=None, pipeline_base=None, chan=None)
        self.config.register_user(email=None)

        GADMIN_COG: Any = self.bot.get_cog("GlobalAdmin")
        if GADMIN_COG:
            GADMIN_COG.register_perm("crud")
        else:
            raise errors.CogLoadError("Global Administration cog must be loaded.  Make sure it's "
                                      "installed from core-cogs and load it via `^load globaladmin`")

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        email = self.config.user_from_id(user_id)
        if email:
            data = f"You have a stored email ({email})"
        else:
            data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data."""
        await self.config.user_from_id(user_id).clear()

    async def get_cursor(self):
        async with aiofiles.open(await self.config.config_file(), 'r') as db_config:
            return (await self.connect(json.loads(await db_config.read()))).cursor()

    async def get_dbcog(self) -> "DBCog":
        dbcog: Any = self.bot.get_cog("DBCog")
        if dbcog is None:
            raise ValueError("DBCog cog is not loaded")
        await dbcog.wait_until_ready()
        return dbcog

    def connect(self, db_config):
        return aiomysql.connect(host=db_config['host'],
                                user=db_config['user'],
                                password=db_config['password'],
                                db=db_config['db'],
                                charset=db_config['charset'],
                                cursorclass=aiomysql.cursors.DictCursor,
                                autocommit=True)

    async def execute_write(self, ctx, sql, replacements):
        async with await self.get_cursor() as cursor:
            affected = await cursor.execute(sql, replacements)
            await ctx.send(inline(sql % replacements))
            await ctx.send("{} row(s) affected.".format(affected))

    async def execute_read(self, ctx, sql, replacements):
        async with await self.get_cursor() as cursor:
            await cursor.execute(sql, replacements)
            results = list(await cursor.fetchall())
            msg = 'Results\n' + json.dumps(results, indent=2, ensure_ascii=False, sort_keys=True)
            await ctx.send(inline(sql % replacements))
            for page in pagify(msg):
                await ctx.send(box(page))

    async def git_verify(self, ctx, folder, filename):
        filepath = folder + filename
        
        try:
            repo = pygit2.Repository(await self.config.pipeline_base())
        except pygit2.GitError:
            return
        if not repo.diff():
            return
        if not repo.lookup_branch("master").is_checked_out():
            await send_cancellation_message(ctx, f"Hey {ctx.author.mention}, the pipeline branch is currently **not**"
                                                 f" set to master! Please inform a sysadmin that this crud change"
                                                 f" was only **temporarily** made!")
            return
        if any(diff for diff in repo.diff().deltas if diff.old_file.path != filepath):
            return await send_cancellation_message(ctx, f"Hey {ctx.author.mention}, there are currently staged changes."
                                                        f" Please inform a sysadmin so that your changes can be"
                                                        f" manually committed.")

        keys = await self.bot.get_shared_api_tokens("github")
        if "username" not in keys or "token" not in keys:
            return await send_cancellation_message(ctx, f"Github credentials unset.  Add via `{ctx.prefix}set api"
                                                        f" github username <username> token <access token>`")

        try:
            index = repo.index
            index.add(filepath)
            index.write()
            tree = index.write_tree()
            email = await self.config.user(ctx.author).email()
            author = pygit2.Signature(re.sub(r'[<>]', '', str(ctx.author)),
                                      email or "famiel@tsubakibot.com")
            commiter = pygit2.Signature("Famiel", "famiel@tsubakibot.com")
            parent, ref = repo.resolve_refish(refish=repo.head.name)
            repo.create_commit(ref.name, author, commiter, f"Updating {filename}", tree, [parent.oid])
            upcred = pygit2.UserPass(keys['username'], keys['token'])
            remote = discord.utils.get(repo.remotes, name="origin")
            remote.push(['refs/heads/master'], callbacks=pygit2.RemoteCallbacks(credentials=upcred))
        except Exception as e:
            logger.exception("Failed to push.")
            await send_cancellation_message(ctx, f"Failed to push to github.  Please alert a sysadmin.")

    @commands.group()
    @auth_check('crud')
    @commands.check(check_crud_channel)
    async def crud(self, ctx):
        """PadGuide database CRUD."""

    @commands.command()
    async def editmonsname(self, ctx, monster_id: int, *, name):
        """Change a monster's name_en_override

        To remove a name override, set the name to None, NULL, or ""
        """
        if name.startswith('"') and name.endswith('"') and name.count('"') <= 2:
            name = name[1:-1]

        if name.lower() in ["none", "null", ""]:
            name = None

        async with await self.get_cursor() as cursor:
            # Get the most recent english translation override
            await cursor.execute("""SELECT 
                                monsters.name_en AS monster_name,
                                monster_name_overrides.name_en AS old_override
                              FROM monster_name_overrides
                              RIGHT JOIN monsters
                                ON monsters.monster_id = monster_name_overrides.monster_id
                              WHERE monsters.monster_id = %s AND (is_translation = 1 OR is_translation IS NULL)
                              ORDER BY monster_name_overrides.tstamp DESC LIMIT 1""", (monster_id,))
            old_val = await cursor.fetchall()

        if not old_val:
            return await ctx.send(f"There is no monster with id {monster_id}")
        monster_name = old_val[0]['monster_name']
        old_name = old_val[0]['old_override']
        if not await get_user_confirmation(ctx, (f"Are you sure you want to change `{monster_name} ({monster_id})`'s"
                                                 f" english override from `{old_name}` to `{name}`?")):
            return

        sql = (f'INSERT INTO monster_name_overrides (monster_id, name_en, is_translation, tstamp)'
               f' VALUES (%s, %s, 1, UNIX_TIMESTAMP())')
        await self.execute_write(ctx, sql, (monster_id, name))

    @crud.command()
    async def searchdungeon(self, ctx, *, search_text):
        """Search for a dungeon via its jp or na name"""
        search_text = '%{}%'.format(search_text).lower()
        sql = ('SELECT dungeon_id, name_en, name_ja, visible FROM dungeons'
               ' WHERE lower(name_en) LIKE %s OR lower(name_ja) LIKE %s'
               ' ORDER BY dungeon_id DESC LIMIT 20')
        await self.execute_read(ctx, sql, (search_text, search_text))

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
        await self.execute_read(ctx, sql, (search_text, search_text))

    @series.command(name="add")
    async def series_add(self, ctx, *elements):
        """Add a new series.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `series_type`

        Example Usage:
        [p]crud series add key1 "Value1" key2 "Value2"
        """
        if not elements:
            return await ctx.send_help()
        if len(elements) % 2 != 0:
            return await send_cancellation_message(ctx, "Imbalanced key-value pairs. Make sure"
                                                        " multi-word values are in quotes")
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in SERIES_KEYS for x in elements)):
            return await send_cancellation_message(ctx, f"Valid keys are {', '.join(map(inline, SERIES_KEYS))}")

        if "series_type" in elements and elements['series_type'] not in SERIES_TYPES:
            return await send_cancellation_message(ctx, "`series_type` must be one of: " + ", ".join(SERIES_TYPES))

        EXTRAS = {}
        async with await self.get_cursor() as cursor:
            await cursor.execute("SELECT MAX(series_id) AS max_id FROM series")
            max_val = (await cursor.fetchall())[0]['max_id']
            EXTRAS['series_id'] = max_val + 1
        EXTRAS['tstamp'] = int(datetime.now().timestamp())
        elements = {**SERIES_KEYS, **EXTRAS, **elements}

        key_infix = ", ".join(elements.keys())
        value_infix = ", ".join("%s" for v in elements.values())
        sql = ('INSERT INTO series ({})'
               ' VALUES ({})').format(key_infix, value_infix)

        await self.execute_write(ctx, sql, (*elements.values(),))

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'series.json')
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
        await self.git_verify(ctx, self.json_folder, 'series.json')

    @series.command(name="edit")
    async def series_edit(self, ctx, series_id: int, *elements):
        """Edit an existing series.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `series_type`

        Example Usage:
        [p]crud series edit 100 key1 "Value1" key2 "Value2"
        """
        if not elements:
            return await ctx.send_help()
        if len(elements) % 2 != 0:
            return await send_cancellation_message(ctx, "Imbalanced key-value pairs. Make sure"
                                                        " multi-word values are in quotes")
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in SERIES_KEYS for x in elements)):
            return await ctx.send_help()

        if "series_type" in elements and elements['series_type'] not in SERIES_TYPES:
            return await ctx.send("`series_type` must be one of: " + ", ".join(SERIES_TYPES))

        replacement_infix = ", ".join(["{} = %s".format(k) for k in elements.keys()])
        sql = ('UPDATE series'
               ' SET {}'
               ' WHERE series_id = %s').format(replacement_infix)

        await self.execute_write(ctx, sql, (*elements.values(), series_id))

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'series.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        for e in j:
            if e['series_id'] == series_id:
                e.update(elements)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))
        await self.git_verify(ctx, self.json_folder, 'series.json')

    @series.command(name="delete")
    @checks.is_owner()
    async def series_delete(self, ctx, series_id: int):
        """Delete an existing series"""
        sql = ('DELETE FROM series'
               ' WHERE series_id = %s')

        await self.execute_write(ctx, sql, series_id)

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'series.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        for e in j[:]:
            if e['series_id'] == series_id:
                j.remove(e)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))
        await self.git_verify(ctx, self.json_folder, 'series.json')

    @crud.group(aliases=["awos"])
    async def awokenskill(self, ctx):
        """Awoken skill related commands"""

    @awokenskill.command(name="search")
    async def awokenskill_search(self, ctx, *, search_text):
        """Search for a awoken skill via its jp or na name"""
        dbcog = await self.get_dbcog()
        if search_text in dbcog.KNOWN_AWOKEN_SKILL_TOKENS:
            where = f'awoken_skill_id = %s'
            replacements = (dbcog.KNOWN_AWOKEN_SKILL_TOKENS[search_text].value,)
        else:
            where = f"lower(name_en) LIKE %s OR lower(name_ja) LIKE %s"
            replacements = ('%{}%'.format(search_text).lower(),) * 2
        sql = (f'SELECT awoken_skill_id, name_en, name_ja, name_ko, desc_en,'
               f' desc_ja, desc_ko FROM awoken_skills'
               f' WHERE {where}'
               f' ORDER BY awoken_skill_id DESC LIMIT 20')
        await self.execute_read(ctx, sql, replacements)

    @awokenskill.command(name="add")
    @checks.is_owner()
    async def awokenskill_add(self, ctx, *elements):
        """Add a new awoken skill.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `desc_en`, `desc_ko`, `desc_ja`

        Example Usage:
        [p]crud awokenskill add key1 "Value1" key2 "Value2"
        """
        if not elements:
            return await ctx.send_help()
        if len(elements) % 2 != 0:
            return await send_cancellation_message(ctx, "Imbalanced key-value pairs. Make sure"
                                                        " multi-word values are in quotes")
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in AWOKEN_SKILL_KEYS for x in elements)):
            return await ctx.send_help()

        if "awoken_skill_id" not in elements or not elements["awoken_skill_id"].isdigit():
            return await ctx.send("You must supply an numeric `awoken_skill_id` when adding a new awoken skill.")
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

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'awoken_skill.json')
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
        await self.git_verify(ctx, self.json_folder, 'awoken_skill.json')

    @awokenskill.command(name="edit")
    async def awokenskill_edit(self, ctx, awoken_skill, *elements):
        """Edit an existing awoken skill.

        Valid element keys are: `name_en`, `name_ko`, `name_ja`, `desc_en`, `desc_ko`, `desc_ja`

        Example Usage:
        [p]crud awokenskill edit 100 key1 "Value1" key2 "Value2"
        [p]crud awokenskill edit misc_comboboost key1 "Value1" key2 "Value2"
        """
        dbcog = await self.get_dbcog()
        if awoken_skill in dbcog.KNOWN_AWOKEN_SKILL_TOKENS:
            awoken_skill_id = dbcog.KNOWN_AWOKEN_SKILL_TOKENS[awoken_skill].value
        elif awoken_skill.isdigit():
            awoken_skill_id = int(awoken_skill)
        else:
            return await ctx.send("Invalid awoken skill.")

        awoken_skill_id = int(awoken_skill_id)

        if not elements:
            return await ctx.send_help()
        if len(elements) % 2 != 0:
            return await send_cancellation_message(ctx, "Imbalanced key-value pairs. Make sure"
                                                        " multi-word values are in quotes")
        elements = {elements[i]: elements[i + 1] for i in range(0, len(elements), 2)}

        if not (elements and all(x in AWOKEN_SKILL_KEYS for x in elements)):
            return await ctx.send_help()

        if 'awoken_skill_id' in elements:
            return await ctx.send("`awoken_skill_id` is not a supported key for editing.")

        replacement_infix = ", ".join(["{} = %s".format(k) for k in elements.keys()])
        sql = ('UPDATE awoken_skills'
               ' SET {}'
               ' WHERE awoken_skill_id = %s').format(replacement_infix)

        await self.execute_write(ctx, sql, (*elements.values(), awoken_skill_id))

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'awoken_skill.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())

        for e in j:
            if e['pad_awakening_id'] == awoken_skill_id:
                e.update(elements)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))
        await self.git_verify(ctx, self.json_folder, 'awoken_skill.json')

    @awokenskill.command(name="delete")
    @checks.is_owner()
    async def awokenskill_delete(self, ctx, awoken_skill_id: int):
        """Delete an existing awoken skill"""
        sql = ('DELETE FROM awoken_skills'
               ' WHERE awoken_skill_id = %s')

        await self.execute_write(ctx, sql, awoken_skill_id)

        fn = os.path.join(await self.config.pipeline_base(), self.json_folder, 'awoken_skill.json')
        async with aiofiles.open(fn, 'r') as f:
            j = json.loads(await f.read())
        for e in j[:]:
            if e['pad_awakening_id'] == awoken_skill_id:
                j.remove(e)
        async with aiofiles.open(fn, 'w') as f:
            await f.write(json.dumps(j, indent=2, ensure_ascii=False, sort_keys=True))
        await self.git_verify(ctx, self.json_folder, 'awoken_skill.json')

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

    @commands.command(aliases=['group#', 'ghgroup#'])
    async def ghgroupn(self, ctx, *, query):
        dbcog: Any = self.bot.get_cog("DBCog")
        if dbcog is None:
            return await ctx.send("DBCog not loaded.")
        monster = await dbcog.find_monster(query, ctx.author.id)
        if monster is None:
            return await ctx.send("No matching monster found.")
        await ctx.send(f"{MonsterHeader.text_with_emoji(monster)} is in GungHo Group #{monster.group_id}")

    @commands.command(aliases=['collab#', 'ghcollab#'])
    async def ghcollabn(self, ctx, *, query):
        dbcog: Any = self.bot.get_cog("DBCog")
        if dbcog is None:
            return await ctx.send("DBCog not loaded.")
        monster = await dbcog.find_monster(query, ctx.author.id)
        if monster is None:
            return await ctx.send("No matching monster found.")
        await ctx.send(f"{MonsterHeader.text_with_emoji(monster)} is in GungHo Collab #{monster.collab_id}")

    @crud.command()
    async def setmyemail(self, ctx, email=None):
        """Sets your email so GitHub commits can be properly attributed"""
        if email is not None and \
                not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email):
            return await ctx.send("Invalid email.")
        await self.config.user(ctx.author).email.set(email)
        await ctx.tick()
