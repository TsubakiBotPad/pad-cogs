import logging
from typing import Any, TYPE_CHECKING

from discordmenu.emoji.emoji_cache import emoji_cache
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from tsutils.enums import Server
from tsutils.user_interaction import send_cancellation_message

from dungeoncog.enemy_skills_pb2 import MonsterBehavior
from dungeoncog.menu.dungeon import DungeonMenu
from dungeoncog.menu.menu_map import dungeon_menu_map
from dungeoncog.view.dungeon import DungeonViewState

if TYPE_CHECKING:
    from dbcog.dungeon_context import DungeonContext

logger = logging.getLogger('red.padbot-cogs.dungeoncog')
EMBED_NOT_GENERATED = -1
DEFAULT_SERVER = Server.COMBINED


class DungeonCog(commands.Cog):
    """
    Contains commands that are display information about dungeons.
    Right now only one command, dungeon_info which displays information such as spawns in a dungeon.
    """
    menu_map = dungeon_menu_map

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        gadmin: Any = self.bot.get_cog("GlobalAdmin")
        if gadmin:
            gadmin.register_perm("contentadmin")

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
            if server is not None:
                # slightly bullshit handling here because we can't have DEFAULT_SERVER imported
                # here due to cross-cog bullshit.
                # please move DEFAULT_SERVER to tsutils or do a proper cross-cog import
                # for a proper patch but this is a hotfix okay
                sub_id = database.get_sub_dungeon_id_from_name(dungeon.dungeon_id, difficulty, server=server)
            else:
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
