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
from functools import reduce

import time
from io import BytesIO
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import discord
from redbot.core import Config, checks, commands, data_manager
from redbot.core.utils.chat_formatting import box, pagify
from tsutils.cogs.globaladmin import auth_check
from tsutils.enums import Server
from tsutils.json_utils import async_cached_dadguide_request, safe_read_json
from tsutils.tsubaki import CLOUDFRONT_URL
from tsutils.user_interaction import StatusManager, send_confirmation_message

from . import token_mappings
from .database_loader import load_database
from .find_monster import FindMonster, MatchMap
from .idtest_mixin import IdTest
from .models.enum_types import DEFAULT_SERVER, SERVERS
from .models.monster_model import MonsterModel
from .models.monster_stats import MonsterStatModifierInput, monster_stats
from .monster_index import MONSTER_ATTR_ALIAS_TO_ATTR_MAP, MONSTER_CLASS_ATTRIBUTES, MonsterIndex

logger = logging.getLogger('red.padbot-cogs.dbcog')


def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='dbcog')), file_name)


class DBCog(commands.Cog, IdTest):
    """Database manager"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self._is_ready = asyncio.Event()

        self.database = None
        self.indexes = {
            Server.COMBINED: MonsterIndex(Server.COMBINED),
            Server.NA: MonsterIndex(Server.NA),
        }

        self.fir_lock = asyncio.Lock()
        self.fir3_lock = asyncio.Lock()

        self.fm_flags_default = {'na_prio': True, 'server': DEFAULT_SERVER}
        self.config = Config.get_conf(self, identifier=64667103)
        self.config.register_global(datafile='', indexlog=0, test_suite={}, fluff_suite=[], typo_mods=[],
                                    debug_mode=False, debug_mode_monsters=[3260])
        self.config.register_user(lastaction=None, fm_flags={})

        self.db_file_path = _data_file('dadguide.sqlite')
        self.historic_lookups_file_path = _data_file('historic_lookups_id3.json')
        self.historic_lookups = safe_read_json(self.historic_lookups_file_path)
        self.monster_stats = monster_stats
        self.MonsterStatModifierInput = MonsterStatModifierInput

        self.token_maps = token_mappings
        self.DEFAULT_SERVER = DEFAULT_SERVER
        self.SERVERS = SERVERS

        self.mon_finder = None  # type: Optional[FindMonster]

        gadmin: Any = self.bot.get_cog("GlobalAdmin")
        if gadmin:
            gadmin.register_perm("contentadmin")

    async def wait_until_ready(self) -> None:
        """Wait until the DBCog cog is ready.

        Call this from other cogs to wait until DBCog finishes refreshing its database
        for the first time.
        """
        await self._is_ready.wait()

    async def wait_until_ready_verbose(self, ctx) -> None:
        """Wait until the DBCog cog is ready but loudly.

        Call this from other cogs to wait until DBCog finishes refreshing its database
        for the first time.
        """
        if self._is_ready.is_set():
            return
        msg = await ctx.send("Index is still loading. Please wait...")
        await self._is_ready.wait()
        try:
            await msg.delete()
        except discord.Forbidden:
            pass

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        udata = await self.config.user_from_id(user_id).ans()

        data = "Your stored query flags are: " + "\n".join(udata['fm_flags'].keys())
        data += f"\nUse '{(await self.bot.get_valid_prefixes())[0]}idset list' to see what they're set to."

        if not udata:
            data = "No data is stored for user with ID {}.\n".format(user_id)

        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data."""
        await self.config.user_from_id(user_id).clear()

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
        for server in SERVERS:
            self.indexes[server] = MonsterIndex(server)
            await self.indexes[server].setup(self.database.graph)

        self.mon_finder = FindMonster(self, self.fm_flags_default)
        asyncio.create_task(self.check_index())

    async def check_index(self):
        issues = []
        issues.extend(self.database.graph.issues)
        for index in self.indexes.values():
            issues.extend(index.issues)
        for class_attributes in MONSTER_CLASS_ATTRIBUTES:
            good = False
            for monster in self.database.get_all_monsters():
                val: Any = monster
                for ca in class_attributes:
                    if not hasattr(val, ca):
                        break
                    val = getattr(val, ca)
                else:
                    break
            else:
                issues.append(f"Invalid class attribute: {'.'.join(class_attributes)}")

        issues.extend(await self.run_tests())

        if issues and self.database.graph.debug_monster_ids is None:
            channels = [self.bot.get_channel(await self.config.indexlog())]
            if not any(channels):
                channels = [owner for oid in self.bot.owner_ids if (owner := self.bot.get_user(oid))]
                for channel in channels:
                    await channel.send("Use `{}dbcog setfailurechannel <channel>`"
                                       " to move these out of your DMs!"
                                       "".format((await self.bot.get_valid_prefixes())[0]))
            for page in pagify(f"Load Warnings:\n" + "\n".join(issues[:100])):
                for channel in channels:
                    await channel.send(box(page))

    def get_monster(self, monster_id: int, *, server: Server = DEFAULT_SERVER) -> Optional[MonsterModel]:
        """Exported function that allows a client cog to get a full MonsterModel by monster_id"""
        return self.database.graph.get_monster(monster_id, server=server)

    def cog_unload(self):
        # Manually nulling out database because the GC for cogs seems to be pretty shitty
        logger.info('Unloading DBCog')
        if self.database:
            self.database.close()
        self.database = None
        self._is_ready.clear()

    async def reload_data_task(self):
        await self.bot.wait_until_ready()

        # We already had a copy of the database at startup, signal that we're ready now.
        if self.database and self.database.has_database():
            logger.info('Using stored database at load')

        while self == self.bot.get_cog('DBCog'):
            short_wait = False
            try:
                async with StatusManager(self.bot):
                    await self.download_and_refresh_nicknames()
                logger.info('Done refreshing DBCog, triggering ready')
                self._is_ready.set()
            except Exception as ex:
                short_wait = True
                logger.exception("DBCog data download/refresh failed: %s", ex)

            try:
                wait_time = 60 if short_wait else 60 * 60 * 4
                await asyncio.sleep(wait_time)
            except Exception as ex:
                logger.exception("DBCog data wait loop failed: %s", ex)
                raise

    async def download_and_refresh_nicknames(self):
        if await self.config.datafile():
            logger.info('Copying dg data file')
            shutil.copy2(await self.config.datafile(), self.db_file_path)
        else:
            logger.info('Downloading dg data files')
            await async_cached_dadguide_request(self.db_file_path,
                                                CLOUDFRONT_URL + '/db/dadguide.sqlite',
                                                1 * 60 * 60)

        logger.info('Loading dg database')
        self.database = load_database(self.database, await self.get_debug_monsters())
        logger.info('Building dg monster index')
        await self.create_index()

        logger.info('Done refreshing dg data')

    @commands.group()
    @checks.is_owner()
    async def dbcog(self, ctx):
        """DBCog database settings"""

    @dbcog.command()
    @checks.is_owner()
    async def setdatafile(self, ctx, data_file):
        """Set a local path to dbcog data instead of downloading it."""
        await self.config.datafile.set(data_file)
        await ctx.tick()

    @dbcog.command()
    @checks.is_owner()
    async def setfailurechannel(self, ctx, channel: discord.TextChannel):
        await self.config.indexlog.set(channel.id)
        await ctx.tick()

    @dbcog.group(aliases=["debug"])
    @checks.is_owner()
    async def debugmode(self, ctx):
        """Tsubaki-Only Mode settings"""

    @debugmode.command(name="enable", aliases=["enabled"])
    async def debug_enable(self, ctx, enabled: bool):
        """Sets tsubaki-only mode and reloads the index and graph"""
        await self.config.debug_mode.set(enabled)
        if enabled:
            await send_confirmation_message(ctx, f"You have set your bot to **Tsubaki mode** (aka debug mode)."
                                                 f" Only **Tsubaki** will be available in the graph and id"
                                                 f" queries, to allow for a faster restart time. To turn"
                                                 f" off **Tsubaki mode** run"
                                                 f" `{ctx.prefix}dbcog debugmode false`.")
        else:
            await send_confirmation_message(ctx, f"You have turned off **Tsubaki mode**. Your bot will behave"
                                                 f" normally. To return to **Tsubaki mode**, run"
                                                 f" `{ctx.prefix}dbcog debugmode true.`")
        await self.forceindexreload(ctx)

    @debugmode.group(name="monsters")
    async def debug_monsters(self, ctx):
        """Monsters allowed in Tsubaki-Only mode"""

    @debug_monsters.command(name="add")
    async def debug_monsters_add(self, ctx, *monsters: int):
        async with self.config.debug_mode_monsters() as ts_monsters:
            for monster in monsters:
                if monster not in ts_monsters:
                    ts_monsters.append(monster)
        if await self.config.debug_mode():
            await self.forceindexreload(ctx)
        await ctx.tick()

    @debug_monsters.command(name="remove", aliases=["rm", "del", "delete"])
    async def debug_monsters_rm(self, ctx, *monsters: int):
        async with self.config.debug_mode_monsters() as ts_monsters:
            for monster in monsters:
                if monster in ts_monsters:
                    ts_monsters.remove(monster)
        if await self.config.debug_mode():
            await self.forceindexreload(ctx)
        await ctx.tick()

    @debug_monsters.command(name="list")
    async def debug_monsters_list(self, ctx):
        text = "\n".join(f'{m} {mon.name_en}' if (mon := self.get_monster(m)) else f"Invalid monster {m}"
                         for m in await self.config.debug_mode_monsters())
        for page in pagify(text):
            await ctx.send(box(page))

    async def get_debug_monsters(self) -> Optional[List[int]]:
        if await self.config.debug_mode():
            return await self.config.debug_mode_monsters()
        return None

    async def get_fm_flags(self, author_id):
        return {**self.fm_flags_default, **(await self.config.user_from_id(author_id).fm_flags())}

    async def find_monster(self, query: str, author_id: int = 0) -> Optional[MonsterModel]:
        return await FindMonster(self, await self.get_fm_flags(author_id)).find_monster(query)

    async def find_monsters(self, query: str, author_id: int = 0) -> List[MonsterModel]:
        return await FindMonster(self, await self.get_fm_flags(author_id)).find_monsters(query)

    async def _find_monster_debug(self, query: str) -> Tuple[Optional[MonsterModel], MatchMap, Set[MonsterModel], int]:
        return await FindMonster(self, self.fm_flags_default).find_monster_debug(query)

    @staticmethod
    def get_aliased_attribute(monster: MonsterModel, alias: str) -> Union[Dict[str, Any], Any]:
        if alias not in MONSTER_ATTR_ALIAS_TO_ATTR_MAP:
            raise ValueError(f"Invalid alias {alias}")

        ret = {}
        keys = [ks for ks in zip(*MONSTER_ATTR_ALIAS_TO_ATTR_MAP[alias])
                if len(ks) == 1 or not reduce(lambda x, y: x == y, ks)].pop()
        for key, attrs in zip(keys, MONSTER_ATTR_ALIAS_TO_ATTR_MAP[alias]):
            value: Any = monster
            for attr in attrs:
                value = getattr(value, attr)
            ret[key] = value
        if len(ret) == 1:
            return set(ret.values()).pop()
        return ret

    @commands.command()
    async def attr(self, ctx, attr, *, query):
        await self.wait_until_ready()
        monster = await self.find_monster(query, ctx.author.id)
        if monster is None:
            return await ctx.send("Sorry, we could not locate this monster")
        try:
            data = self.get_aliased_attribute(monster, attr)
        except ValueError:
            return await ctx.send("Sorry, this attribute is not recognized")
        except AttributeError:
            return await ctx.send("Sorry, {} doesn't have this attribute".format(monster.name_en))
        if not isinstance(data, dict):
            return await ctx.send(data)
        for k, v in data.items():
            if k.endswith('_en'):
                return await ctx.send(v)
        return await ctx.send('\n'.join([f"**{k}**: {v}" for k, v in data.items()]))
