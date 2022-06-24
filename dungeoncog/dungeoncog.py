import asyncio
import csv
import io
import logging
from collections import defaultdict
from typing import Any, TYPE_CHECKING

import aiohttp
from discordmenu.emoji.emoji_cache import emoji_cache
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from tsutils.cogs.globaladmin import auth_check
from tsutils.enums import Server
from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.user_interaction import send_cancellation_message

from dbcog.models.enum_types import DEFAULT_SERVER
from dungeoncog.enemy_skills_pb2 import MonsterBehavior
from dungeoncog.menu.closable_embed import ClosableEmbedMenu
from dungeoncog.menu.dungeon import DungeonMenu
from dungeoncog.menu.menu_map import dungeon_menu_map
from dungeoncog.view.dungeon import DungeonViewState
from dungeoncog.view.skyo_links import SkyoLinksView, SkyoLinksViewProps

if TYPE_CHECKING:
    from dbcog.database_manager import DBCogDatabase
    from dbcog.dungeon_context import DungeonContext

logger = logging.getLogger('red.padbot-cogs.dungeoncog')
EMBED_NOT_GENERATED = -1

DUNGEON_ALIASES = "https://docs.google.com/spreadsheets/d/e/" \
                  "2PACX-1vQ3F4shS6w2na4FXA-vZyyhKcOQ0zRA1B3T7zaX0Bm4cEjW-1IVw91josPtLgc9Zh_TGh8GTD6zFmd0" \
                  "/pub?gid=0&single=true&output=csv"


class DungeonCog(commands.Cog):
    """
    Contains commands that are display information about dungeons.
    Right now only one command, dungeon_info which displays information such as spawns in a dungeon.
    """
    menu_map = dungeon_menu_map

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.aliases = defaultdict(set)
        self.aliases_loaded = asyncio.Event()

        gadmin: Any = self.bot.get_cog("GlobalAdmin")
        if gadmin:
            gadmin.register_perm("contentadmin")

    async def load_aliases(self):
        self.aliases_loaded.clear()
        self.aliases = defaultdict(set)
        async with aiohttp.ClientSession() as session:
            async with session.get(DUNGEON_ALIASES) as response:
                reader = csv.reader(io.StringIO(await response.text()), delimiter=',')
        next(reader)
        for line in reader:
            for a in line[2].replace(' ', '').split(','):
                self.aliases[a].add(line[0] or line[1])
        self.aliases_loaded.set()

    async def load_emojis(self):
        await self.bot.wait_until_ready()
        emoji_cache.set_guild_ids([g.id for g in self.bot.guilds])
        emoji_cache.refresh_from_discord_bot(self.bot)

    async def register_menu(self):
        await self.bot.wait_until_ready()
        menulistener = self.bot.get_cog("MenuListener")
        if menulistener is None:
            logger.warning("MenuListener is not loaded.")
            return
        await menulistener.register(self)

    async def get_menu_default_data(self, ims):
        data = {
            'dbcog': await self.get_dbcog(),
        }
        return data

    async def get_dbcog(self):
        dbcog = self.bot.get_cog("DBCog")
        if dbcog is None:
            raise ValueError("DBCog cog is not loaded")
        await dbcog.wait_until_ready()
        return dbcog

    async def find_dungeon_from_name(self, ctx, name, database: "DungeonContext", difficulty: str = None,
                                     server: Server = DEFAULT_SERVER):
        """
        Gets the sub_dungeon model given the name of a dungeon and its difficulty.
        """
        dungeons = database.get_dungeons_from_nickname(name.lower(), server=server)
        if not dungeons:
            dungeons = database.get_dungeons_from_name(name, server=server)
            if len(dungeons) == 0:
                return None
            if len(dungeons) > 1:
                return dungeons
            dungeon = dungeons.pop()
            sub_id = database.get_sub_dungeon_id_from_name(dungeon.dungeon_id, difficulty, server=server)
            sub_dungeon_model = None
            if sub_id is None:
                sub_id = 0
                for sd in dungeon.sub_dungeons:
                    if sd.sub_dungeon_id > sub_id:
                        sub_id = sd.sub_dungeon_id
                        sub_dungeon_model = sd
            else:
                for sd in dungeon.sub_dungeons:
                    if sd.sub_dungeon_id == sub_id:
                        sub_dungeon_model = sd
                        break
            dungeon.sub_dungeons = [sub_dungeon_model]
        else:
            dungeon = dungeons.pop()
        return dungeon

    @commands.command(aliases=['dgid'], ignore_extra=False)
    async def dungeonid(self, ctx, dungeon_name, floor_name=None):
        """Get encounter data for a dungeon.

        Quotes must be used around multi-word names
        [p]dungeonid "blue bowl dragon"
        [p]dungeonid "ultimate arena" "three hands of fate"
        [p]dungeonid "castle of satan in the abyss" 3
        """
        dbcog = await self.get_dbcog()
        dungeon = await self.find_dungeon_from_name(ctx, dungeon_name, dbcog.database.dungeon, floor_name)

        if dungeon is None:
            return await send_cancellation_message(ctx, "No dungeons found!")
        if type(dungeon) == list:
            header = "Multiple Dungeons Found, please be more specific:\n"
            for page in pagify(header + '\n'.join(d.name_en for d in dungeon)):
                await ctx.send(page)
            return
        # await ctx.send(format_overview(test_result))
        current_stage = 0
        pm_dungeon = []
        # check for invades:
        invades = []

        # print(dungeon.sub_dungeons[0].encounter_models)
        for enc_model in dungeon.sub_dungeons[0].encounter_models:
            behavior_test = MonsterBehavior()
            if (enc_model.enemy_data is not None) and (enc_model.enemy_data.behavior is not None):
                behavior_test.ParseFromString(enc_model.enemy_data.behavior)
            else:
                behavior_test = None

            # await ctx.send(format_overview(test_result))
            # pm = process_monster(behavior_test, enc_model, db_cog.database)
            if enc_model.stage < 0:
                # pm.am_invade = True
                invades.append(enc_model)
            elif enc_model.stage > current_stage:
                current_stage = enc_model.stage
                floor = [enc_model]
                pm_dungeon.append(floor)
            else:
                pm_dungeon[current_stage - 1].append(enc_model)
        for f in pm_dungeon:
            if pm_dungeon.index(f) != (len(pm_dungeon) - 1):
                f.extend(invades)

        if len(pm_dungeon) == 0:
            return await send_cancellation_message(ctx, "This dungeon exists, but we have no data for it")

        menu = DungeonMenu.menu()
        original_author_id = ctx.message.author.id
        view_state = DungeonViewState(original_author_id, 'DungeonMenu', dungeon_name, pm_dungeon[0][0],
                                      dungeon.sub_dungeons[0].sub_dungeon_id, len(pm_dungeon), 1,
                                      len(pm_dungeon[0]), 0,
                                      int(dungeon.sub_dungeons[0].technical), dbcog.database, verbose=False)
        await ctx.send(
            "EN: {}({})\nJP: {}({})".format(dungeon.name_en, dungeon.sub_dungeons[0].name_en, dungeon.name_ja,
                                            dungeon.sub_dungeons[0].name_ja))
        await menu.create(ctx, view_state)

    @commands.command()
    async def skyo(self, ctx, *, search_text):
        """Show the subdungeon ids of all matching dungeons"""
        dbcog = await self.get_dbcog()
        db: "DBCogDatabase" = dbcog.database.database

        query_settings = await QuerySettings.extract_raw(ctx.author, self.bot, search_text)

        await self.aliases_loaded.wait()
        if search_text.replace(' ', '') not in self.aliases:
            formatted_text = f'%{search_text}%'
            sds = db.query_many(
                'SELECT dungeons.dungeon_id, sub_dungeon_id, dungeons.name_en AS dg_name, sub_dungeons.name_en AS sd_name'
                ' FROM sub_dungeons'
                ' JOIN dungeons ON sub_dungeons.dungeon_id = dungeons.dungeon_id'
                ' WHERE LOWER(dungeons.name_en) LIKE ? OR LOWER(dungeons.name_ja) LIKE ?'
                ' OR LOWER(sub_dungeons.name_en) LIKE ? OR LOWER(sub_dungeons.name_ja) LIKE ?'
                ' ORDER BY dungeons.dungeon_id LIMIT 20', (formatted_text,) * 4)
        else:
            formatted_text = ', '.join(a for a in self.aliases[search_text.replace(' ', '')] if a.isnumeric())
            sds = db.query_many(
                'SELECT dungeons.dungeon_id, sub_dungeon_id, dungeons.name_en AS dg_name, sub_dungeons.name_en AS sd_name'
                ' FROM sub_dungeons'
                ' JOIN dungeons ON sub_dungeons.dungeon_id = dungeons.dungeon_id'
                f' WHERE dungeons.dungeon_id IN ({formatted_text}) OR sub_dungeon_id IN ({formatted_text})'
                ' ORDER BY dungeons.dungeon_id LIMIT 20')

        if not sds:
            return await ctx.send(f"No dungeons found")

        dungeons = defaultdict(lambda: {'subdungeons': []})
        for sd in sds:
            dungeons[sd.dungeon_id]['name'] = sd.dg_name
            dungeons[sd.dungeon_id]['idx'] = sd.dungeon_id
            dungeons[sd.dungeon_id]['subdungeons'].append({
                'name': sd.sd_name,
                'idx': sd.sub_dungeon_id})

        menu = ClosableEmbedMenu.menu()
        props = SkyoLinksViewProps(sorted(dungeons.values(), key=lambda d: d['idx']))
        state = ClosableEmbedViewState(ctx.message.author.id, ClosableEmbedMenu.MENU_TYPE, search_text,
                                       query_settings, SkyoLinksView.VIEW_TYPE, props)
        return await menu.create(ctx, state)

    @commands.command(aliases=['firdg'])
    @auth_check('contentadmin')
    async def force_dungeon_index_reload(self, ctx):
        async with ctx.typing():
            await self.load_aliases()
        await ctx.send("Reloaded")
