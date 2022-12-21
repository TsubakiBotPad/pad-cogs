import json
import logging
import re
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
from crud.tables.awoken_skills import CRUDAwokenSkills
from crud.tables.latent_skills import CRUDLatentSkills
from crud.tables.series import CRUDSeries

if TYPE_CHECKING:
    from dbcog import DBCog

logger = logging.getLogger('red.padbot-cogs.crud')


async def check_crud_channel(ctx):
    chan = await ctx.bot.get_cog("Crud").config.chan()
    return chan is None or chan == ctx.channel.id or ctx.author.id in ctx.bot.owner_ids


class Crud(CRUDSeries, CRUDAwokenSkills, CRUDLatentSkills, EditSeries):
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
        self.setup_mixins()

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = '\n'.join(await self.get_mixin_user_data(user_id))

        email = self.config.user_from_id(user_id)
        if email:
            data += f"You have a stored email ({email})\n"

        if not data:
            data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data."""
        await self.config.user_from_id(user_id).clear()
        await self.delete_mixin_user_data(requester, user_id)

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
