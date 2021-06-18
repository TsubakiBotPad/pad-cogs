import logging
import os

import discord
from discord import Color
from discordmenu.emoji.emoji_cache import emoji_cache
from redbot.core import commands, data_manager

from dungeon.enemy_skills_pb2 import MonsterBehavior
from dungeon.menu.dungeon import DungeonMenu, DungeonMenuPanes
from dungeon.menu.menu_map import dungeon_menu_map
from dungeon.view.dungeon import DungeonViewState

logger = logging.getLogger('red.padbot-cogs.dungeon')
EMBED_NOT_GENERATED = -1


def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='dungeon')), file_name)


RAW_ENEMY_SKILLS_URL = 'https://d1kpnpud0qoyxf.cloudfront.net/ilmina/download_enemy_skill_data.json'
RAW_ENEMY_SKILLS_DUMP = _data_file('enemy_skills.json')


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
                return None
            if len(dungeons) > 1:
                message = "Multiple Dungeons Found, please be more specific:"
                for d in dungeons:
                    message += "\n{}".format(d.name_en)
                await ctx.send(message)
                return None
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

    async def _do_menu(self, ctx, starting_menu_emoji, emoji_to_embed, timeout=60):
        if starting_menu_emoji not in emoji_to_embed.emoji_dict:
            # Selected menu wasn't generated for this monster
            return EMBED_NOT_GENERATED

        emoji_to_embed.emoji_dict[self.menu.emoji.get("no")] = self.menu.reaction_delete_message

        try:
            result_msg, result_embed = await self.menu.custom_menu(ctx, emoji_to_embed,
                                                                   starting_menu_emoji, timeout=timeout)
            if result_msg and result_embed:
                # Message is finished but not deleted, clear the footer
                result_embed.set_footer(text=discord.Embed.Empty)
                await result_msg.edit(embed=result_embed)
                await result_msg.e
        except Exception as ex:
            logger.error('Menu failure', exc_info=True)

    @commands.command()
    async def dgid(self, ctx, name: str, difficulty: str = None):
        '''
        Name: Name of Dungeon
        Difficulty: Difficulty level/name of floor (eg. for A1, "Bipolar Goddess")
        '''
        # load dadguide cog for database access
        dgcog = self.bot.get_cog('Dadguide')
        if not dgcog:
            logger.warning("Cog 'Dadguide' not loaded")
            return
        logger.info('Waiting until DG is ready')
        await dgcog.wait_until_ready()
        dungeon = await self.find_dungeon_from_name2(ctx=ctx, name=name, database=dgcog.database.dungeon,
                                                     difficulty=difficulty)

        if dungeon is not None:
            # await ctx.send(formatOverview(test_result))
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

                # await ctx.send(formatOverview(test_result))
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
            full_reaction_list = [emoji_cache.get_by_name(e) for e in DungeonMenuPanes.emoji_names()]
            test_list = ['1', '2', '3', '4']
            # print(pm_dungeon[0])
            view_state = DungeonViewState(original_author_id, 'DungeonMenu', name, Color.default(), pm_dungeon[0][0],
                                          dungeon.sub_dungeons[0].sub_dungeon_id, len(pm_dungeon), 1,
                                          len(pm_dungeon[0]), 0,
                                          int(dungeon.sub_dungeons[0].technical), dgcog.database, verbose=False,
                                          reaction_list=full_reaction_list)
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
