"""
Provides access to DadGuide data.

Access via the exported DadGuide sqlite database.

Don't hold on to any of the dastructures exported from here, or the
entire database could be leaked when the module is reloaded.
"""
import asyncio
import csv
import os
import shutil
from collections import defaultdict
from io import BytesIO
from typing import Optional

import tsutils
from redbot.core import checks, data_manager
from redbot.core import commands

from . import token_mappings
from .database_loader import load_database
from .database_manager import *
from .models.monster_model import MonsterModel
from .models.monster_stats import monster_stats, MonsterStatModifierInput
from .monster_index import MonsterIndex2

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


class Dadguide(commands.Cog):
    """Dadguide database manager"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self._is_ready = asyncio.Event()

        self.settings = DadguideSettings("dadguide")

        # A string -> int mapping, nicknames to monster_id_na
        self.nickname_overrides = {}

        # An int -> set(string), monster_id_na to set of treename overrides
        self.treename_overrides = defaultdict(set)

        self.panthname_overrides = defaultdict(set)

        # Map of google-translated JP names to EN names
        self.translated_names = {}

        self.database = None
        self.index2 = None  # type: Optional[MonsterIndex2]

        self.monster_stats = monster_stats
        self.MonsterStatModifierInput = MonsterStatModifierInput

        self.token_maps = token_mappings

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

    async def create_index2(self):
        """Exported function that allows a client cog to create an id3 monster index"""
        await self.wait_until_ready()
        return await MonsterIndex2(self.database.get_all_monsters(False), self.database)

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

    async def reload_config_files(self):
        os.remove(NICKNAME_FILE_PATTERN)
        os.remove(TREENAME_FILE_PATTERN)
        os.remove(PANTHNAME_FILE_PATTERN)
        await self.download_and_refresh_nicknames()

    async def download_and_refresh_nicknames(self):
        if self.settings.data_file():
            logger.info('Copying dg data file')
            shutil.copy2(self.settings.data_file(), DB_DUMP_FILE)
        else:
            logger.info('Downloading dg data files')
            await self._download_files()

        logger.info('Downloading dg name override files')
        await self._download_override_files()

        logger.info('Loading dg name overrides')
        nickname_overrides = self._csv_to_tuples(NICKNAME_FILE_PATTERN, 6)
        treename_overrides = self._csv_to_tuples(TREENAME_FILE_PATTERN, 6)
        panthname_overrides = self._csv_to_tuples(PANTHNAME_FILE_PATTERN, 3)

        self.nickname_overrides = defaultdict(set)
        for id, nick, _, _, _, i in nickname_overrides:
            if id.isdigit() and not i:
                self.nickname_overrides[int(id)].add(nick.lower())

        self.treename_overrides = defaultdict(set)
        for id, treename, _, _, _, i in treename_overrides:
            if id.isdigit() and not i:
                self.treename_overrides[int(id)].add(treename.lower())

        self.panthname_overrides = {x[1].lower(): x[2].lower() for x in panthname_overrides}
        self.panthname_overrides.update({v: v for _, v in self.panthname_overrides.items()})

        logger.info('Loading dg database')
        self.database = load_database(self.database)
        logger.info('Building dg monster index')
        self.index2 = await MonsterIndex2(self.database.get_all_monsters(False), self.database)

        logger.info('Done refreshing dg data')

    def _csv_to_tuples(self, file_path: str, cols: int = 2):
        # Loads a two-column CSV into an array of tuples.
        results = []
        with open(file_path, encoding='utf-8') as f:
            file_reader = csv.reader(f, delimiter=',')
            for row in file_reader:
                if len(row) < 2:
                    continue

                data = [None] * cols
                for i in range(0, min(cols, len(row))):
                    data[i] = row[i].strip()

                if not len(data[0]):
                    continue

                results.append(data)
        return results

    async def _download_files(self):
        one_hour_secs = 1 * 60 * 60
        await tsutils.async_cached_dadguide_request(DB_DUMP_FILE, DB_DUMP_URL, one_hour_secs)

    async def _download_override_files(self):
        one_hour_secs = 1 * 60 * 60
        await tsutils.async_cached_plain_request(
            NICKNAME_FILE_PATTERN, NICKNAME_OVERRIDES_SHEET, one_hour_secs)
        await tsutils.async_cached_plain_request(
            TREENAME_FILE_PATTERN, GROUP_TREENAMES_OVERRIDES_SHEET, one_hour_secs)
        await tsutils.async_cached_plain_request(
            PANTHNAME_FILE_PATTERN, PANTHNAME_OVERRIDES_SHEET, one_hour_secs)

    @commands.group()
    @checks.is_owner()
    async def dadguide(self, ctx):
        """Dadguide database settings"""

    @dadguide.command()
    @checks.is_owner()
    async def setdatafile(self, ctx, *, data_file):
        """Set a local path to dadguide data instead of downloading it."""
        self.settings.set_data_file(data_file)
        await ctx.tick()


class DadguideSettings(tsutils.CogSettings):
    def make_default_settings(self):
        config = {
            'data_file': '',
        }
        return config

    def data_file(self):
        return self.bot_settings['data_file']

    def set_data_file(self, data_file):
        self.bot_settings['data_file'] = data_file
        self.save_settings()
