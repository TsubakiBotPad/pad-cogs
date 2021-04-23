"""
Provides access to DadGuide data.

Access via the exported DadGuide sqlite database.

Don't hold on to any of the dastructures exported from here, or the
entire database could be leaked when the module is reloaded.
"""
import asyncio
import logging
import os
import shutil
from io import BytesIO
from typing import Optional, List

import discord
import time
import tsutils
from redbot.core import checks, data_manager, commands, Config
from redbot.core.utils.chat_formatting import pagify, box
from tsutils import auth_check, safe_read_json

from . import token_mappings
from .find_monster import FindMonster
from .database_loader import load_database
from .idtest_mixin import IdTest
from .models.monster_model import MonsterModel
from .models.monster_stats import monster_stats, MonsterStatModifierInput
from .monster_index import MonsterIndex

logger = logging.getLogger('red.padbot-cogs.dadguide')


def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='dadguide')), file_name)


try:
    # allow to run the tests locally without being inside a bot instance, which won't
    # have any cog data path loaded
    CSV_FILE_PATTERN = '{}.csv'
    NAMES_EXPORT_PATH = _data_file('computed_names.json')
    TREENAMES_EXPORT_PATH = _data_file('base_names.json')
    TRANSLATEDNAMES_EXPORT_PATH = _data_file('translated_names.json')

    SHEETS_PATTERN = 'https://docs.google.com/spreadsheets/d/1EoZJ3w5xsXZ67kmarLE4vfrZSIIIAfj04HXeZVST3eY/pub?gid={}&single=true&output=csv'
    NICKNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('0')
    GROUP_TREENAMES_OVERRIDES_SHEET = SHEETS_PATTERN.format('2070615818')
    PANTHNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('959933643')

    NICKNAME_FILE_PATTERN = _data_file(CSV_FILE_PATTERN.format('nicknames'))
    TREENAME_FILE_PATTERN = _data_file(CSV_FILE_PATTERN.format('treenames'))
    PANTHNAME_FILE_PATTERN = _data_file(CSV_FILE_PATTERN.format('panthnames'))

    DB_DUMP_URL = 'https://d1kpnpud0qoyxf.cloudfront.net/db/dadguide.sqlite'
    DB_DUMP_FILE = _data_file('dadguide.sqlite')
except RuntimeError:
    pass


class Dadguide(commands.Cog, IdTest):
    """Dadguide database manager"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self._is_ready = asyncio.Event()

        self.database = None
        self.index = None  # type: Optional[MonsterIndex]

        self.fir_lock = asyncio.Lock()
        self.fir3_lock = asyncio.Lock()

        self.fm_flags_default = {'na_prio': True}
        self.config = Config.get_conf(self, identifier=64667103)
        self.config.register_global(datafile='', indexlog=0, test_suite={}, fluff_suite=[], typo_mods=[])
        self.config.register_user(lastaction=None, fm_flags={})

        self.historic_lookups_file_path = _data_file('historic_lookups_id3.json')
        self.historic_lookups = safe_read_json(self.historic_lookups_file_path)
        self.monster_stats = monster_stats
        self.MonsterStatModifierInput = MonsterStatModifierInput

        self.token_maps = token_mappings
        self.mon_finder = FindMonster(self, self.fm_flags_default)

        GADMIN_COG = self.bot.get_cog("GlobalAdmin")
        if GADMIN_COG:
            GADMIN_COG.register_perm("contentadmin")

    async def wait_until_ready(self):
        """Wait until the Dadguide cog is ready.

        Call this from other cogs to wait until Dadguide finishes refreshing its database
        for the first time.
        """
        return await self._is_ready.wait()

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    @commands.command(aliases=['fir'])
    @auth_check('contentadmin')
    async def forceindexreload(self, ctx):
        if self.fir_lock.locked():
            await ctx.send("Index is already being reloaded.")
            return

        async with ctx.typing(), self.fir_lock:
            start = time.perf_counter()
            await ctx.send('Starting reload...')
            await self.wait_until_ready()
            await self.download_and_refresh_nicknames()
            await ctx.send('Reload finished in {} seconds.'.format(round(time.perf_counter() - start, 2)))

    @commands.command(aliases=['fir3'])
    @auth_check('contentadmin')
    async def forceindexreload3(self, ctx):
        if self.fir3_lock.locked():
            await ctx.send("Index is already being reloaded.")
            return

        async with ctx.typing(), self.fir3_lock:
            start = time.perf_counter()
            await self.wait_until_ready()
            await self.create_index()
            await ctx.send('Reload finished in {} seconds.'.format(round(time.perf_counter() - start, 2)))

    async def create_index(self):
        """Exported function that allows a client cog to create an id3 monster index"""
        self.index = await MonsterIndex(self.database.get_all_monsters(), self.database)  # noqa
        asyncio.create_task(self.check_index())

    async def check_index(self):
        if not await self.config.indexlog():
            return

        self.index.issues.extend((await self.run_tests())[:25])

        channel = self.bot.get_channel(await self.config.indexlog())
        if self.index.issues:
            for page in pagify("Index Load Warnings:\n" + "\n".join(self.index.issues[:100])):
                await channel.send(box(page))

    def get_monster(self, monster_id: int) -> MonsterModel:
        """Exported function that allows a client cog to get a full MonsterModel by monster_id"""
        return self.database.graph.get_monster(monster_id)

    def cog_unload(self):
        # Manually nulling out database because the GC for cogs seems to be pretty shitty
        logger.info('Unloading Dadguide')
        if self.database:
            self.database.close()
        self.database = None
        self._is_ready.clear()

    async def reload_data_task(self):
        await self.bot.wait_until_ready()

        # We already had a copy of the database at startup, signal that we're ready now.
        if self.database and self.database.has_database():
            logger.info('Using stored database at load')

        while self == self.bot.get_cog('Dadguide'):
            short_wait = False
            try:
                async with tsutils.StatusManager(self.bot):
                    await self.download_and_refresh_nicknames()
                logger.info('Done refreshing Dadguide, triggering ready')
                self._is_ready.set()
            except Exception as ex:
                short_wait = True
                logger.exception("dadguide data download/refresh failed: %s", ex)

            try:
                wait_time = 60 if short_wait else 60 * 60 * 4
                await asyncio.sleep(wait_time)
            except Exception as ex:
                logger.exception("dadguide data wait loop failed: %s", ex)
                raise ex

    async def download_and_refresh_nicknames(self):
        if await self.config.datafile():
            logger.info('Copying dg data file')
            shutil.copy2(await self.config.datafile(), DB_DUMP_FILE)
        else:
            logger.info('Downloading dg data files')
            await self._download_files()

        logger.info('Loading dg database')
        self.database = load_database(self.database)
        logger.info('Building dg monster index')
        await self.create_index()

        logger.info('Done refreshing dg data')

    async def _download_files(self):
        one_hour_secs = 1 * 60 * 60
        await tsutils.async_cached_dadguide_request(DB_DUMP_FILE, DB_DUMP_URL, one_hour_secs)

    @commands.group()
    @checks.is_owner()
    async def dadguide(self, ctx):
        """Dadguide database settings"""

    @dadguide.command()
    @checks.is_owner()
    async def setdatafile(self, ctx, data_file):
        """Set a local path to dadguide data instead of downloading it."""
        await self.config.datafile.set(data_file)
        await ctx.tick()

    @dadguide.command()
    @checks.is_owner()
    async def setindexlog(self, ctx, channel: discord.TextChannel):
        await self.config.indexlog.set(channel.id)
        await ctx.tick()

    async def get_fm_flags(self, author_id):
        # noinspection PyTypeChecker
        return {**self.fm_flags_default, **(await self.config.user(discord.Object(author_id)).fm_flags())}

    async def find_monster(self, query: str, author_id: int = 0) -> MonsterModel:
        return await FindMonster(self, await self.get_fm_flags(author_id)).find_monster(query)

    async def find_monsters(self, query: str, author_id: int = 0) -> List[MonsterModel]:
        return await FindMonster(self, await self.get_fm_flags(author_id)).find_monsters(query)
