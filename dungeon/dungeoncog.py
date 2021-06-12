import logging
import os

import discord
from discord import Color
from discordmenu.emoji.emoji_cache import emoji_cache

from tsutils import Menu, EmojiUpdater
from redbot.core import commands, data_manager
from dadguide.dungeon_context import DungeonContext
from dungeon.SafeDict import SafeDict
from dungeon.enemy_skills_pb2 import MonsterBehavior, LevelBehavior, BehaviorGroup, Condition, Behavior
from collections import OrderedDict

from dungeon.dungeon_monster import DungeonMonster
from redbot.core.utils.chat_formatting import pagify

# If these are unused remember to remove
from dungeon.menu.dungeon import DungeonMenu, DungeonMenuPanes
from dungeon.menu.menu_map import dungeon_menu_map
from dungeon.menu.simple import SimpleMenu, SimpleEmoji, SimpleMenuPanes
from dungeon.processors import process_monster, formatOverview
from dungeon.view.dungeon import DungeonViewState
from dungeon.view.simple import SimpleViewState

logger = logging.getLogger('red.padbot-cogs.padinfo')
EMBED_NOT_GENERATED = -1

dungeon_query = '''
SELECT
monsters.name_en,
dungeons.dungeon_id,
dungeons.name_en as dungeon_name_en,
sub_dungeons.name_en as sub_name_en,
sub_dungeons.technical,
encounters.*,
enemy_data.behavior
FROM
encounters
LEFT OUTER JOIN dungeons ON encounters.dungeon_id = dungeons.dungeon_id
LEFT OUTER JOIN enemy_data ON encounters.enemy_id = enemy_data.enemy_id
LEFT OUTER JOIN monsters ON encounters.monster_id = monsters.monster_id
LEFT OUTER JOIN sub_dungeons on sub_dungeons.sub_dungeon_id = encounters.sub_dungeon_id
WHERE
encounters.sub_dungeon_id = {}
ORDER BY
encounters.stage
'''

dungeon_search_query = '''
SELECT
DISTINCT
dungeons.name_en,
dungeons.dungeon_id
FROM 
dungeons
LEFT OUTER JOIN encounters ON dungeons.dungeon_id = encounters.dungeon_id
WHERE
dungeons.name_en LIKE "{}%" 
AND 
EXISTS 
(SELECT encounters.sub_dungeon_id WHERE encounters.dungeon_id = dungeons.dungeon_id)
'''

"""We are looking for the highest difficulty"""

dungeon_sub_id_query = '''
SELECT
dungeons.name_en,
dungeons.dungeon_id,
encounters.sub_dungeon_id
FROM
dungeons
LEFT OUTER JOIN encounters ON dungeons.dungeon_id = encounters.dungeon_id
WHERE
dungeons.dungeon_id = {}
ORDER BY
encounters.sub_dungeon_id DESC
'''

sub_dungeons_query = '''
SELECT
sub_dungeons.*
FROM
sub_dungeons
WHERE 
sub_dungeons.dungeon_id = {} AND
sub_dungeons.name_en LIKE "%{}%"
ORDER BY
sub_dungeons.sub_dungeon_id
'''

encounter_query = '''
SELECT
monsters.name_en,
monsters.name_ja,
monsters.name_ko,
encounters.*,
enemy_data.behavior,
enemy_data.status
FROM
encounters
LEFT OUTER JOIN enemy_data ON encounters.enemy_id = enemy_data.enemy_id
LEFT OUTER JOIN monsters ON encounters.monster_id = monsters.monster_id
WHERE
encounters.encounter_id = {}
'''

sub_dungeon_exists_query = '''
SELECT
encounters.sub_dungeon_id
FROM
encounters
WHERE
encounters.sub_dungeon_id = {}
'''

skill_query = '''
SELECT
enemy_skills.*
FROM
enemy_skills
WHERE
enemy_skill_id = {}
'''

DungeonNickNames = {
    'a1': 1022001,
    'arena1': 102201,
    'bipolar goddess 1': 1022001,
    'bp1': 1022001,
    'a2': 1022002,
    'arena2': 102202,
    'bipolar goddess 2': 1022002,
    'bp2': 1022002,
    'a3': 1022003,
    'arena3': 102203,
    'bipolar goddess 3': 1022003,
    'bp3': 1022003,
    'a4': 1022004,
    'arena4': 102204,
    'three hands of fate': 1022004,
    'thof': 1022004,
    'a5': 1022005,
    'arena5': 102205,
    'incarnation of worlds': 1022005,
    'iow': 1022005,
    'aa1': 2660001,
    'aa2': 2660002,
    'aa3': 2660003,
    'aa4': 2660004,
    'shura1': 4400001,
    'shura2': 4401001,
    'iwoc': 4400001,
    'alt. iwoc': 4400001,
}


def _data_file(file_name: str) -> str:
    return os.path.join(str(data_manager.cog_data_path(raw_name='dungeon')), file_name)


RAW_ENEMY_SKILLS_URL = 'https://d1kpnpud0qoyxf.cloudfront.net/ilmina/download_enemy_skill_data.json'
RAW_ENEMY_SKILLS_DUMP = _data_file('enemy_skills.json')

class DungeonEmojiUpdater(EmojiUpdater):
    # DungeonEmojiUpdater takes a starting monster, starting floor (list of monsters) and the dungeon (array of floors)
    """
    Emoji:
    <<, >> previous and next monster of the current floor (a floor is a list of potential spawns of the floor)
    <, > (not implemented) previous and next page of the current monster
    up and down arrows are go up one floor and go down one floor
    """

    def __init__(self, ctx, emoji_to_embed, dungeon_cog=None, selected_emoji=None, pm: DungeonMonster = None,
                 pm_dungeon: "list[list[DungeonMonster]]" = None, pm_floor: "list[DungeonMonster]" = None,
                 technical: int = None, compacts=None, verboses=None, preempts=None):
        self.emoji_dict = emoji_to_embed
        self.selected_emoji = selected_emoji
        self.pm = pm
        self.pm_floor = pm_floor
        self.pm_dungeon = pm_dungeon
        self.ctx = ctx
        self.dungeon_cog = dungeon_cog
        self.technical = technical
        self.current_page = 0
        self.compacts = compacts
        self.verboses = verboses
        self.preempts = preempts
        self.current_pages = self.compacts

    async def on_update(self, ctx, selected_emoji):
        index_monster = self.pm_floor.index(self.pm)
        index_floor = self.pm_dungeon.index(self.pm_floor)
        update = False
        if selected_emoji == self.dungeon_cog.previous_monster_emoji:
            self.pm = self.pm_floor[index_monster - 1]
            if index_monster == 0:
                index_monster = len(self.pm_floor) - 1
            else:
                index_monster -= 1
            update = True
        elif selected_emoji == self.dungeon_cog.next_monster_emoji:
            if index_monster == len(self.pm_floor) - 1:
                self.pm = self.pm_floor[0]
                index_monster = 0
            else:
                self.pm = self.pm_floor[index_monster + 1]
                index_monster += 1
            update = True

        elif selected_emoji == self.dungeon_cog.previous_floor:
            self.pm_floor = self.pm_dungeon[index_floor - 1]
            self.pm = self.pm_floor[0]
            if index_floor == 0:
                index_floor = len(self.pm_dungeon) - 1
            else:
                index_floor -= 1
            index_monster = 0
            update = True
        elif selected_emoji == self.dungeon_cog.next_floor:
            if index_floor == len(self.pm_dungeon) - 1:
                self.pm_floor = self.pm_dungeon[0]
                index_floor = 0
            else:
                self.pm_floor = self.pm_dungeon[index_floor + 1]
                index_floor += 1
            self.pm = self.pm_floor[0]
            index_monster = 0
            update = True
        elif selected_emoji == self.dungeon_cog.next_page:
            # print(self.compacts)
            if self.current_page == 0:
                self.current_page = -1
            else:
                self.current_page = 0
        elif selected_emoji == self.dungeon_cog.current_monster:
            self.current_pages = self.compacts
        elif selected_emoji == self.dungeon_cog.verbose_monster:
            self.current_pages = self.verboses
        elif selected_emoji == self.dungeon_cog.preempt_monster:
            self.current_pages = self.preempts
        else:
            self.selected_emoji = selected_emoji
            return True

        if update:
            self.compacts = self.pm.make_embed(verbose=False, spawn=[index_monster + 1, len(self.pm_floor)],
                                               floor=[index_floor + 1, len(self.pm_dungeon)],
                                               technical=self.technical)
            self.verboses = self.pm.make_embed(verbose=True, spawn=[index_monster + 1, len(self.pm_floor)],
                                               floor=[index_floor + 1, len(self.pm_dungeon)],
                                               technical=self.technical)
            self.preempts = self.pm.make_embed(spawn=[index_monster + 1, len(self.pm_floor)],
                                               floor=[index_floor + 1, len(self.pm_dungeon)],
                                               technical=self.technical)
        if selected_emoji != self.dungeon_cog.next_page:
            self.current_page = 0

        self.emoji_dict = await self.dungeon_cog.make_emoji_dictionary(self.ctx,
                                                                       compact_page=self.compacts[self.current_page],
                                                                       verbose_page=self.verboses[self.current_page],
                                                                       preempt_page=self.preempts[self.current_page],
                                                                       show=len(self.current_pages) > 1)
        return True


# From pad-data-pipeline
"""
Give a condition type, output a player readable string that actually explains what it does
"""


class DungeonCog(commands.Cog):
    """My custom cog"""
    menu_map = dungeon_menu_map

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.menu = Menu(bot)
        self.previous_monster_emoji = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
        self.previous_page = '\N{BLACK LEFT-POINTING TRIANGLE}'
        self.next_page = '\N{BLACK RIGHT-POINTING TRIANGLE}'
        self.next_monster_emoji = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'
        self.next_page = '📖'
        self.remove_emoji = self.menu.emoji['no']
        self.next_floor = '\N{UPWARDS BLACK ARROW}'
        self.previous_floor = '\N{DOWNWARDS BLACK ARROW}'
        self.current_monster = '👹'
        self.verbose_monster = '📜'
        self.preempt_monster = '⚡'
        self.emoji_map = SafeDict(resolve_status=emoji_cache.get_by_name('resolve'),
                                  fire_orb=emoji_cache.get_by_name('orb_fire'),
                                  recover_health=emoji_cache.get_by_name('misc_autoheal'),
                                  roulette=emoji_cache.get_by_name('spinner'),
                                  unknown_type='Unknown',
                                  defense_status=emoji_cache.get_by_name('defense'),
                                  combo_absorb_status=emoji_cache.get_by_name('combo'),
                                  absorb_status=emoji_cache.get_by_name('attribute_absorb'),
                                  damage_absorb_status=emoji_cache.get_by_name('damage_absorb'),
                                  damage_void_status=emoji_cache.get_by_name('vdp'),
                                  status_shield_status=emoji_cache.get_by_name('status'),
                                  movetime_buff_status=emoji_cache.get_by_name('time_buff'),
                                  movetime_debuff_status=emoji_cache.get_by_name('time_debuff'),
                                  dispel_status='Dispel',
                                  leader_swap_status=emoji_cache.get_by_name('swap'),
                                  skill_delay=emoji_cache.get_by_name('misc_sb'),
                                  lock_orbs=emoji_cache.get_by_name('lock'),
                                  tape_status=emoji_cache.get_by_name('res_seal'),
                                  fixed_start=emoji_cache.get_by_name('orb_start'),
                                  cloud_status=emoji_cache.get_by_name('res_cloud'),
                                  gravity=emoji_cache.get_by_name('gravity'),
                                  invincible_status=emoji_cache.get_by_name('invincible'),
                                  invincible_off_status=emoji_cache.get_by_name('invincible'),  # TODO
                                  force_target_status=emoji_cache.get_by_name('force_target'),
                                  leader_alter_status=emoji_cache.get_by_name('transform'),
                                  board_size_status=emoji_cache.get_by_name('board_size'),
                                  super_resolve_status=emoji_cache.get_by_name('super_resolve'),
                                  turn_change=emoji_cache.get_by_name('turn_change'),
                                  enrage_status=emoji_cache.get_by_name('enrage'),
                                  active_skill_bind=emoji_cache.get_by_name('skill_bound'),
                                  do_nothing="💤",
                                  awoken_bind=emoji_cache.get_by_name('awoken_bound'),
                                  no_skyfall_status=emoji_cache.get_by_name('no_skyfall'),
                                  bind=emoji_cache.get_by_name('res_bind'),
                                  skyfall_status='🌧',
                                  blind='⚫',
                                  super_blind=emoji_cache.get_by_name('blind_orb'),
                                  to='➡️',
                                  attack=emoji_cache.get_by_name('single_hit'),
                                  multi_attack=emoji_cache.get_by_name('multi_hit'),
                                  target_self='Self',
                                  health=emoji_cache.get_by_name('health'),
                                  combo_orb=emoji_cache.get_by_name('orb_combo'),
                                  locked_bomb_orb=emoji_cache.get_by_name('locked_bomb_orb'),
                                  random_attribute='Random Att',
                                  water_orb=emoji_cache.get_by_name('orb_water'),
                                  wood_orb=emoji_cache.get_by_name('orb_wood'),
                                  light_orb=emoji_cache.get_by_name('orb_light'),
                                  dark_orb=emoji_cache.get_by_name('orb_dark'),
                                  healer_orb=emoji_cache.get_by_name('heal_orb'),
                                  jammer_orb=emoji_cache.get_by_name('jammer_orb'),
                                  poison_orb=emoji_cache.get_by_name('poison_orb'),
                                  bomb_orb=emoji_cache.get_by_name('bomb_orb'),
                                  mortal_poison_orb=emoji_cache.get_by_name('mortal_poison_orb'),
                                  evo_material_type=emoji_cache.get_by_name('killer_evomat'),
                                  balanced_type=emoji_cache.get_by_name('killer_balance'),
                                  physical_type=emoji_cache.get_by_name('killer_physical'),
                                  healer_type=emoji_cache.get_by_name('killer_healer'),
                                  dragon_type=emoji_cache.get_by_name('killer_dragon'),
                                  god_type=emoji_cache.get_by_name('killer_god'),
                                  attacker_type=emoji_cache.get_by_name('killer_attacker'),
                                  devil_type=emoji_cache.get_by_name('killer_devil'),
                                  machine_type=emoji_cache.get_by_name('killer_machine'),
                                  awakening_material_type=emoji_cache.get_by_name('killer_awoken'),
                                  enhance_material_type=emoji_cache.get_by_name('killer_enhancemat'),
                                  redeemable_material_type='🪙'
                                  )

    async def load_emojis(self):
        await self.bot.wait_until_ready()
        logging.debug('load_emojis, dungeon')
        emoji_cache.set_guild_ids([g.id for g in self.bot.guilds])
        emoji_cache.refresh_from_discord_bot(self.bot)
        self.emoji_map = SafeDict(resolve_status=emoji_cache.get_by_name('resolve'),
                                  fire_orb=emoji_cache.get_by_name('orb_fire'),
                                  recover_health=emoji_cache.get_by_name('misc_autoheal'),
                                  roulette=emoji_cache.get_by_name('spinner'),
                                  unknown_type='Unknown',
                                  defense_status=emoji_cache.get_by_name('defense'),
                                  combo_absorb_status=emoji_cache.get_by_name('combo'),
                                  absorb_status=emoji_cache.get_by_name('attribute_absorb'),
                                  damage_absorb_status=emoji_cache.get_by_name('damage_absorb'),
                                  damage_void_status=emoji_cache.get_by_name('vdp'),
                                  status_shield_status=emoji_cache.get_by_name('status'),
                                  movetime_buff_status=emoji_cache.get_by_name('time_buff'),
                                  movetime_debuff_status=emoji_cache.get_by_name('time_debuff'),
                                  dispel_status='Dispel',
                                  leader_swap_status=emoji_cache.get_by_name('swap'),
                                  skill_delay=emoji_cache.get_by_name('misc_sb'),
                                  lock_orbs=emoji_cache.get_by_name('lock'),
                                  tape_status=emoji_cache.get_by_name('res_seal'),
                                  fixed_start=emoji_cache.get_by_name('orb_start'),
                                  cloud_status=emoji_cache.get_by_name('res_cloud'),
                                  gravity=emoji_cache.get_by_name('gravity'),
                                  invincible_status=emoji_cache.get_by_name('invincible'),
                                  invincible_off_status=emoji_cache.get_by_name('invincible'),  # TODO
                                  force_target_status=emoji_cache.get_by_name('force_target'),
                                  leader_alter_status=emoji_cache.get_by_name('transform'),
                                  board_size_status=emoji_cache.get_by_name('board_size'),
                                  super_resolve_status=emoji_cache.get_by_name('super_resolve'),
                                  turn_change=emoji_cache.get_by_name('turn_change'),
                                  enrage_status=emoji_cache.get_by_name('enrage'),
                                  active_skill_bind=emoji_cache.get_by_name('skill_bound'),
                                  do_nothing="💤",
                                  awoken_bind=emoji_cache.get_by_name('awoken_bound'),
                                  no_skyfall_status=emoji_cache.get_by_name('no_skyfall'),
                                  bind=emoji_cache.get_by_name('res_bind'),
                                  skyfall_status='🌧',
                                  blind='⚫',
                                  super_blind=emoji_cache.get_by_name('blind_orb'),
                                  to='➡️',
                                  attack=emoji_cache.get_by_name('single_hit'),
                                  multi_attack=emoji_cache.get_by_name('multi_hit'),
                                  target_self='Self',
                                  health=emoji_cache.get_by_name('health'),
                                  combo_orb=emoji_cache.get_by_name('orb_combo'),
                                  locked_bomb_orb=emoji_cache.get_by_name('locked_bomb_orb'),
                                  random_attribute='Random Att',
                                  water_orb=emoji_cache.get_by_name('orb_water'),
                                  wood_orb=emoji_cache.get_by_name('orb_wood'),
                                  light_orb=emoji_cache.get_by_name('orb_light'),
                                  dark_orb=emoji_cache.get_by_name('orb_dark'),
                                  healer_orb=emoji_cache.get_by_name('orb_heal'),
                                  jammer_orb=emoji_cache.get_by_name('jammer_orb'),
                                  poison_orb=emoji_cache.get_by_name('poison_orb'),
                                  bomb_orb=emoji_cache.get_by_name('bomb_orb'),
                                  mortal_poison_orb=emoji_cache.get_by_name('mortal_poison_orb'),
                                  evo_material_type=emoji_cache.get_by_name('killer_evomat'),
                                  balanced_type=emoji_cache.get_by_name('killer_balance'),
                                  physical_type=emoji_cache.get_by_name('killer_physical'),
                                  healer_type=emoji_cache.get_by_name('killer_healer'),
                                  dragon_type=emoji_cache.get_by_name('killer_dragon'),
                                  god_type=emoji_cache.get_by_name('killer_god'),
                                  attacker_type=emoji_cache.get_by_name('killer_attacker'),
                                  devil_type=emoji_cache.get_by_name('killer_devil'),
                                  machine_type=emoji_cache.get_by_name('killer_machine'),
                                  awakening_material_type=emoji_cache.get_by_name('killer_awoken'),
                                  enhance_material_type=emoji_cache.get_by_name('killer_enhancemat'),
                                  redeemable_material_type='🪙'
                                  )

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

    async def find_dungeon_from_name2(self, ctx, name: str, database: DungeonContext, difficulty: str = None):
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

    @commands.command()
    async def test_menu2(self, ctx, message):
        menu = SimpleMenu.menu()
        original_author_id = ctx.message.author.id
        full_reaction_list = [emoji_cache.get_by_name(e) for e in SimpleMenuPanes.emoji_names()]
        test_list = ['1', '2', '3', '4']
        view_state = SimpleViewState(original_author_id, 'SimpleMenu', message, Color.default(), test_list, 0,
                                     reaction_list=full_reaction_list)
        message = await menu.create(ctx, view_state)
        await ctx.send("This is a test of menu2")

    @commands.command()
    async def test(self, ctx):
        dg_cog = self.bot.get_cog('Dadguide')
        # Your code will go here
        if not dg_cog:
            logger.warning("Cog 'Dadguide' not loaded")
            return
        logger.info('Waiting until DG is ready')
        await dg_cog.wait_until_ready()
        context: DungeonContext = dg_cog.database.dungeon
        dung = context.get_dungeons_from_name("Raziel")[0]
        dung2 = await self.find_dungeon_from_name2(ctx, "Raziel", context, "Mythical")

        message = "Dung1:"
        for sd in dung.sub_dungeons:
            message += "\n" + sd.name_en
        message += "\nDung2:"
        for sd in dung2.sub_dungeons:
            message += "\n" + sd.name_en
        await ctx.send(message)

    async def make_emoji_dictionary(self, ctx, scroll_monsters=None, scroll_floors=None, compact_page=None,
                                    verbose_page=None, preempt_page=None, show=False):
        if scroll_monsters is None:
            scroll_monsters = []
        if scroll_floors is None:
            scroll_floors = []
        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.current_monster] = compact_page
        emoji_to_embed[self.verbose_monster] = verbose_page
        emoji_to_embed[self.preempt_monster] = preempt_page
        emoji_to_embed[self.previous_monster_emoji] = None
        emoji_to_embed[self.next_monster_emoji] = None
        emoji_to_embed[self.previous_floor] = None
        emoji_to_embed[self.next_floor] = None
        if show:
            emoji_to_embed[self.next_page] = None

        emoji_to_embed[self.menu.emoji['no']] = self.menu.reaction_delete_message
        return emoji_to_embed

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
    async def dungeon_encounters(self, ctx, name: str, difficulty: str = None):
        """
        List encounters you will find in a dungeon. Mostly for debug.
        Name: Dungeon
        Difficulty: Difficulty level/name of floor (eg. for A1, "Bipolar Goddess")
        """
        dg_cog = self.bot.get_cog('Dadguide')
        if not dg_cog:
            logger.warning("Cog 'Dadguide' not loaded")
            return
        logger.info('Waiting until DG is ready')
        await dg_cog.wait_until_ready()

        sub_id = await self.find_dungeon_from_name(ctx=ctx, name=name, database=dg_cog.database, difficulty=difficulty)
        if sub_id is None:
            return
        test_result = dg_cog.database.database.query_many(dungeon_query.format(sub_id), ())
        if test_result is None:
            await ctx.send("Dungeon not Found")
        else:
            for page in pagify(formatOverview(test_result)):
                await ctx.send(page)

    # 1 is Condensed, 2 is detailed, 3 is preempts
    @commands.command()
    async def dungeon_info(self, ctx, name: str, difficulty: str = None, starting: int = 1):
        '''
        Name: Name of Dungeon
        Difficulty: Difficulty level/name of floor (eg. for A1, "Bipolar Goddess")
        Starting: Starting screen: 1 is condensed information. 2 is detailed information. 3 is preempts only
        '''
        # load dadguide cog for database access
        start_selection = {1: self.current_monster,
                           2: self.verbose_monster,
                           3: self.preempt_monster}
        dg_cog = self.bot.get_cog('Dadguide')
        if not dg_cog:
            logger.warning("Cog 'Dadguide' not loaded")
            return
        logger.info('Waiting until DG is ready')
        await dg_cog.wait_until_ready()
        dungeon = await self.find_dungeon_from_name2(ctx=ctx, name=name, database=dg_cog.database.dungeon,
                                                     difficulty=difficulty)

        if dungeon is not None:
            # await ctx.send(formatOverview(test_result))
            current_stage = 0
            pm_dungeon = []
            # check for invades:
            invades = []
            for enc_model in dungeon.sub_dungeons[0].encounter_models:
                behavior_test = MonsterBehavior()
                if (enc_model.enemy_data is not None) and (enc_model.enemy_data.behavior is not None):
                    behavior_test.ParseFromString(enc_model.enemy_data.behavior)
                else:
                    behavior_test = None

                # await ctx.send(formatOverview(test_result))
                pm = process_monster(behavior_test, enc_model, dg_cog.database)
                if enc_model.stage < 0:
                    pm.am_invade = True
                    invades.append(pm)
                elif enc_model.stage > current_stage:
                    current_stage = enc_model.stage
                    floor = [pm]
                    pm_dungeon.append(floor)
                else:
                    pm_dungeon[current_stage - 1].append(pm)
            for f in pm_dungeon:
                if pm_dungeon.index(f) != (len(pm_dungeon) - 1):
                    f.extend(invades)

            pm = pm_dungeon[0][0]
            compacts = pm.make_embed(verbose=False, spawn=[1, len(pm_dungeon[0])],
                                     floor=[1, len(pm_dungeon)], technical=int(dungeon.sub_dungeons[0].technical))
            verboses = pm.make_embed(verbose=True, spawn=[1, len(pm_dungeon[0])],
                                     floor=[1, len(pm_dungeon)], technical=int(dungeon.sub_dungeons[0].technical))
            preempts = pm.make_embed(spawn=[1, len(pm_dungeon[0])],
                                     floor=[1, len(pm_dungeon)], technical=int(dungeon.sub_dungeons[0].technical))
            emoji_to_embed = await self.make_emoji_dictionary(ctx, compact_page=compacts[0], verbose_page=verboses[0],
                                                              preempt_page=preempts[0], show=len(compacts) > 1)
            dmu = DungeonEmojiUpdater(ctx, emoji_to_embed, self, start_selection[starting], pm_dungeon[0][0],
                                      pm_dungeon, pm_dungeon[0], technical=int(dungeon.sub_dungeons[0].technical),
                                      compacts=compacts, verboses=verboses, preempts=preempts)
            await self._do_menu(ctx, start_selection[starting], dmu, 60)

    @commands.command()
    async def dungeon_info2(self, ctx, name: str, difficulty: str = None, starting: int = 1):
        '''
        Name: Name of Dungeon
        Difficulty: Difficulty level/name of floor (eg. for A1, "Bipolar Goddess")
        '''
        # load dadguide cog for database access
        start_selection = {1: self.current_monster,
                           2: self.verbose_monster,
                           3: self.preempt_monster}
        dg_cog = self.bot.get_cog('Dadguide')
        if not dg_cog:
            logger.warning("Cog 'Dadguide' not loaded")
            return
        logger.info('Waiting until DG is ready')
        await dg_cog.wait_until_ready()
        dungeon = await self.find_dungeon_from_name2(ctx=ctx, name=name, database=dg_cog.database.dungeon,
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
                                          int(dungeon.sub_dungeons[0].technical), dg_cog.database, verbose=False,
                                          reaction_list=full_reaction_list)
            await ctx.send("EN: {}({})\nJP: {}({})".format(dungeon.name_en, dungeon.sub_dungeons[0].name_en, dungeon.name_ja, dungeon.sub_dungeons[0].name_ja))
            message = await menu.create(ctx, view_state)

    @commands.command()
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
        await ctx.send(embed=embed)