import logging
from typing import TYPE_CHECKING

from discordmenu.emoji.emoji_cache import emoji_cache
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify, box
from tsutils.menu.view.closable_embed import ClosableEmbedViewState
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.user_interaction import send_cancellation_message

from dungeoncog.enemy_skills_pb2 import MonsterBehavior
from dungeoncog.menu.closable_embed import ClosableEmbedMenu
from dungeoncog.menu.dungeon import DungeonMenu
from dungeoncog.menu.menu_map import dungeon_menu_map
from dungeoncog.view.dungeon import DungeonViewState
from dungeoncog.view.skyo_links import SkyoLinksViewProps, SkyoLinksView

if TYPE_CHECKING:
    from dbcog.database_manager import DBCogDatabase
    from dbcog.dungeon_context import DungeonContext

logger = logging.getLogger('red.padbot-cogs.dungeoncog')
EMBED_NOT_GENERATED = -1


class DungeonCog(commands.Cog):
    """
    Contains commands that are display information about dungeons.
    Right now only one command, dungeon_info which displays information such as spawns in a dungeon.
    """
    menu_map = dungeon_menu_map

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

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

    async def find_dungeon_from_name(self, ctx, name, database: "DungeonContext", difficulty: str = None):
        """
        Gets the sub_dungeon model given the name of a dungeon and its difficulty.
        """
        dungeons = database.get_dungeons_from_nickname(name.lower())
        if not dungeons:
            dungeons = database.get_dungeons_from_name(name)
            if len(dungeons) == 0:
                return None
            if len(dungeons) > 1:
                return dungeons
            dungeon = dungeons.pop()
            sub_id = database.get_sub_dungeon_id_from_name(dungeon.dungeon_id, difficulty)
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

    @commands.command(aliases=['dgid'])
    async def dungeonid(self, ctx, name, difficulty=None, *bad: str):
        """
        Name: Name of Dungeon
        Difficulty: Difficulty level/name of floor (eg. for A1, "Bipolar Goddess")
        """
        if bad:
            await send_cancellation_message(ctx, "Too many arguments.  Make sure to surround all"
                                                 " arguments with spaces in quotes.")
            return

        # load dbcog cog for database access
        dbcog = await self.get_dbcog()
        dungeon = await self.find_dungeon_from_name(ctx, name, dbcog.database.dungeon, difficulty)

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
        view_state = DungeonViewState(original_author_id, 'DungeonMenu', name, pm_dungeon[0][0],
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

        formatted_text = f'"%{search_text}%"'
        dgs = db.query_many(
            f'SELECT dungeon_id, name_en FROM dungeons'
            f' WHERE LOWER(name_en) LIKE {formatted_text} OR LOWER(name_ja) LIKE {formatted_text}'
            f' ORDER BY dungeon_id LIMIT 20')
        if not dgs:
            return await ctx.send(f"No dungeons found")

        dungeons = []
        for dg in dgs:
            subdgs = db.query_many(f"SELECT sub_dungeon_id, name_en FROM sub_dungeons"
                                   f" WHERE dungeon_id = {dg['dungeon_id']}"
                                   f" ORDER BY sub_dungeon_id")
            dg_dict = {
                'name': dg['name_en'],
                'idx': dg['dungeon_id'],
                'subdungeons': [],
            }
            for subdg in subdgs:
                dg_dict['subdungeons'].append({
                    'name': subdg['name_en'],
                    'idx': subdg['sub_dungeon_id'],
                })
            dungeons.append(dg_dict)

        menu = ClosableEmbedMenu.menu()
        props = SkyoLinksViewProps(dungeons)
        state = ClosableEmbedViewState(ctx.message.author.id, ClosableEmbedMenu.MENU_TYPE, search_text,
                                       query_settings, SkyoLinksView.VIEW_TYPE, props)
        return await menu.create(ctx, state)
