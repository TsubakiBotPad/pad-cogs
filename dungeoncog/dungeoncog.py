import logging
import os
from typing import TYPE_CHECKING

from discord import Color
from discordmenu.emoji.emoji_cache import emoji_cache
from redbot.core import commands, data_manager
from redbot.core.utils.chat_formatting import pagify

from dungeoncog.enemy_skills_pb2 import MonsterBehavior
from dungeoncog.menu.dungeon import DungeonMenu
from dungeoncog.menu.menu_map import dungeon_menu_map
from dungeoncog.view.dungeon import DungeonViewState

if TYPE_CHECKING:
    from dadguide.dungeon_context import DungeonContext

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
        logging.debug('load_emojis, dungeon')
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
            'dgcog': await self.get_dgcog(),
            'color': Color.default()
        }
        return data

    async def get_dgcog(self):
        dgcog = self.bot.get_cog("Dadguide")
        if dgcog is None:
            raise ValueError("Dadguide cog is not loaded")
        await dgcog.wait_until_ready()
        return dgcog

    async def find_dungeon_from_name2(self, ctx, name: str, database: "DungeonContext", difficulty: str = None):
        """
        Gets the sub_dungeon model given the name of a dungeon and its difficulty.
        """
        dungeon = database.get_dungeons_from_nickname(name.lower())
        if dungeon is None:
            dungeons = database.get_dungeons_from_name(name)
            if len(dungeons) == 0:
                await ctx.send("No dungeons found!")
                return
            if len(dungeons) > 1:
                header = "Multiple Dungeons Found, please be more specific:\n"
                for page in pagify(header + '\n'.join(d.name_en for d in dungeons)):
                    await ctx.send(page)
                return
            dungeon = dungeons[0]
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
            dungeon = dungeon[0]
        return dungeon

    @commands.command(aliases=['dgid'])
    async def dungeonid(self, ctx, name, difficulty = None, *bad: str):
        """
        Name: Name of Dungeon
        Difficulty: Difficulty level/name of floor (eg. for A1, "Bipolar Goddess")
        """
        if bad:
            await ctx.send("Too many arguments.  Make sure to surround all"
                           " arguments with spaces in quotes.")
            return

        # load dadguide cog for database access
        dgcog = await self.get_dgcog()
        dungeon = await self.find_dungeon_from_name2(ctx, name, dgcog.database.dungeon, difficulty)

        if dungeon is not None:
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
                # pm = process_monster(behavior_test, enc_model, dg_cog.database)
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

            menu = DungeonMenu.menu()
            original_author_id = ctx.message.author.id
            test_list = ['1', '2', '3', '4']
            # print(pm_dungeon[0])
            view_state = DungeonViewState(original_author_id, 'DungeonMenu', name, Color.default(), pm_dungeon[0][0],
                                          dungeon.sub_dungeons[0].sub_dungeon_id, len(pm_dungeon), 1,
                                          len(pm_dungeon[0]), 0,
                                          int(dungeon.sub_dungeons[0].technical), dgcog.database, verbose=False)
            await ctx.send(
                "EN: {}({})\nJP: {}({})".format(dungeon.name_en, dungeon.sub_dungeons[0].name_en, dungeon.name_ja,
                                                dungeon.sub_dungeons[0].name_ja))
            message = await menu.create(ctx, view_state)


'''    @commands.command()
    async def spinner_help(self, ctx, spin_time, move_time):
        """
        spin_time: The cycle the spinner is set at (typically changes once every second)
        move_time: How much time you have to move orbs
        """
        embed = discord.Embed(title="Spinner Helper {}s Rotation {}s Move Time".format(spin_time, move_time),
                              description="Assuming orbs are set and are NOT moved during movement:")
        casino = ["🔥", "🌊", "🌿", "💡", "🌙", "🩹"]
        cycles = float(move_time) / float(spin_time)
        rounded = int(cycles)
        casino_dict = OrderedDict()
        for c in casino:
            casino_dict.update({c: casino[(casino.index(c) + rounded) % 6]})
        casino_dict.update({"Other": casino[(rounded - 1) % 6]})
        output = ""
        for k, v in casino_dict.items():
            output += "\n{} {} {}".format(k, "➡", v)
        embed.add_field(name="Original -> Final", value=output)
        await ctx.send(embed=embed)'''
