import asyncio
import logging
import os
import urllib.request
from io import BytesIO
from typing import List

import discord
import tsutils

from tsutils import Menu, EmojiUpdater
from redbot.core import commands, data_manager

from google.protobuf import text_format

from dadguide import DadguideDatabase, database_manager
from dungeon.EnemySkillDatabase import EnemySkillDatabase
from dungeon.encounter import Encounter
from dungeon.enemy_skill import process_enemy_skill, ProcessedSkill
from dungeon.enemy_skill_parser import process_enemy_skill2, emoji_dict
from dungeon.enemy_skills_pb2 import MonsterBehavior, LevelBehavior, BehaviorGroup, Condition, Behavior
from collections import OrderedDict

from dungeon.grouped_skillls import GroupedSkills
from dungeon.processed_monster import ProcessedMonster
from redbot.core.utils.chat_formatting import pagify

# If these are unused remember to remove
"""import numpy as np
import pandas as pd
from pyppeteer import launch"""
logger = logging.getLogger('red.padbot-cogs.padinfo')
EMBED_NOT_GENERATED = -1

test_query = '''
SELECT
dungeons.dungeon_id,
dungeons.name_en,
encounters.*,
enemy_data.behavior
FROM
encounters
LEFT OUTER JOIN dungeons ON encounters.dungeon_id = dungeons.dungeon_id
LEFT OUTER JOIN enemy_data ON encounters.enemy_id = enemy_data.enemy_id
WHERE
encounters.sub_dungeon_id = 4301003
ORDER BY
encounters.sub_dungeon_id
'''

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

GroupType = {
    0: "Unspecified",
    1: "Passive",
    2: "Preemptive",
    3: "Dispel Player",
    4: "Monster Status",
    5: "Remaining",
    6: "Standard",
    7: "Death",
    8: "Unknown",
    9: "Highest Priority"
}

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

    def __init__(self, ctx, emoji_to_embed, dungeon_cog=None, selected_emoji=None, pm: ProcessedMonster = None,
                 pm_dungeon: "list[list[ProcessedMonster]]" = None, pm_floor: "list[ProcessedMonster]" = None,
                 technical: int = None):
        self.emoji_dict = emoji_to_embed
        self.selected_emoji = selected_emoji
        self.pm = pm
        self.pm_floor = pm_floor
        self.pm_dungeon = pm_dungeon
        self.ctx = ctx
        self.dungeon_cog = dungeon_cog
        self.technical = technical

    async def on_update(self, ctx, selected_emoji):
        index_monster = self.pm_floor.index(self.pm)
        index_floor = self.pm_dungeon.index(self.pm_floor)
        if selected_emoji == self.dungeon_cog.previous_monster_emoji:
            self.pm = self.pm_floor[index_monster - 1]
            if index_monster == 0:
                index_monster = len(self.pm_floor) - 1
            else:
                index_monster -= 1
        elif selected_emoji == self.dungeon_cog.next_monster_emoji:
            if index_monster == len(self.pm_floor) - 1:
                self.pm = self.pm_floor[0]
                index_monster = 0
            else:
                self.pm = self.pm_floor[index_monster + 1]
                index_monster += 1
        elif selected_emoji == self.dungeon_cog.previous_floor:
            self.pm_floor = self.pm_dungeon[index_floor - 1]
            self.pm = self.pm_floor[0]
            if index_floor == 0:
                index_floor = len(self.pm_dungeon) - 1
            else:
                index_floor -= 1
            index_monster = 0
        elif selected_emoji == self.dungeon_cog.next_floor:
            if index_floor == len(self.pm_dungeon) - 1:
                self.pm_floor = self.pm_dungeon[0]
                index_floor = 0
            else:
                self.pm_floor = self.pm_dungeon[index_floor + 1]
                index_floor += 1
            self.pm = self.pm_floor[0]
            index_monster = 0
        else:
            self.selected_emoji = selected_emoji
            return True

        self.emoji_dict = await self.dungeon_cog.make_emoji_dictionary(self.ctx, self.pm, floor_info=[index_monster + 1,
                                                                                                      len(
                                                                                                          self.pm_floor)],
                                                                       dungeon_info=[index_floor + 1,
                                                                                     len(self.pm_dungeon)],
                                                                       technical=self.technical)
        return True


# From pad-data-pipeline
"""
Give a condition type, output a player readable string that actually explains what it does
"""


def format_condition(cond: Condition):
    parts = []
    if cond.skill_set:
        parts.append('SkillSet {}'.format(cond.skill_set))
    if cond.use_chance not in [0, 100]:
        parts.append('{}% chance'.format(cond.use_chance))
    if cond.global_one_time:
        parts.append('one time only')
    if cond.limited_execution:
        parts.append('at most {} times'.format(cond.limited_execution))
    if cond.trigger_enemies_remaining:
        parts.append('when {} enemies remain'.format(cond.trigger_enemies_remaining))
    if cond.if_defeated:
        parts.append('when defeated')
    if cond.if_attributes_available:
        parts.append('when required attributes on board')
    if cond.trigger_monsters:
        parts.append('when {} on team'.format(', '.join(map(str, cond.trigger_monsters))))
    if cond.trigger_combos:
        parts.append('when {} combos last turn'.format(cond.trigger_combos))
    if cond.if_nothing_matched:
        parts.append('if no other skills matched')
    if cond.repeats_every:
        if cond.trigger_turn:
            if cond.trigger_turn_end:
                parts.append('execute repeatedly, turn {}-{} of {}'.format(cond.trigger_turn,
                                                                           cond.trigger_turn_end,
                                                                           cond.repeats_every))
            else:
                parts.append('execute repeatedly, turn {} of {}'.format(cond.trigger_turn, cond.repeats_every))
        else:
            parts.append('repeats every {} turns'.format(cond.repeats_every))
    elif cond.trigger_turn_end:
        turn_text = 'turns {}-{}'.format(cond.trigger_turn, cond.trigger_turn_end)
        parts.append(_cond_hp_timed_text(cond.always_trigger_above, turn_text))
    elif cond.trigger_turn:
        turn_text = 'turn {}'.format(cond.trigger_turn)
        parts.append(_cond_hp_timed_text(cond.always_trigger_above, turn_text))

    if not parts and cond.hp_threshold in [100, 0]:
        return None

    if cond.hp_threshold == 101:
        parts.append('when hp is full')
    elif cond.hp_threshold:
        parts.append('hp <= {}'.format(cond.hp_threshold))

    return ', '.join(parts)


# From pad-data-pipeline
def _cond_hp_timed_text(always_trigger_above: int, turn_text: str) -> str:
    text = turn_text
    if always_trigger_above == 1:
        text = 'always {}'.format(turn_text)
    elif always_trigger_above:
        text = '{} while HP > {}'.format(turn_text, always_trigger_above)
    return text


def format_behavior_embed(behavior: Behavior, database, embed, group_type: str, q: dict, indent=""):
    skill = database.database.query_one(skill_query.format(behavior.enemy_skill_id), ())
    if skill is None:
        return "Unknown"
    skill_name = skill["name_en"]
    skill_effect = skill["desc_en"]
    condition = format_condition(behavior.condition)
    if condition is not None:
        condition = "**Condition: {}**".format(condition)
    else:
        condition = ""
    # output += indent + 'Skill Name: ' + skill_name
    embed.add_field(
        name="{}Skill Name: {}{}".format(group_type, skill_name, process_enemy_skill(skill_effect, q, skill)),
        value="{}Effect: {}\n{}".format(indent, skill_effect, condition), inline=False)
    # embed.add_field(name="{}Skill{}".format(group_type, skill_name, process_enemy_skill(skill_effect)), value="{}Effect: {}\n{}".format(indent, skill_effect, condition), inline=False)

    # output += '\n{}Effect: '.format(indent) + skill_effect


def format_behavior_group_embed(group: BehaviorGroup, database: DadguideDatabase, embed, q: dict, indent="",
                                preempt_only: bool = False):
    condition = format_condition(group.condition)
    if condition is not None:
        # output += "\n{}Condition: {}".format(indent, condition)
        embed.add_field(name="{}Condition: {}".format(indent, condition), value="Following skills are part of a group",
                        inline=False)
        # indent += "\u200b \u200b \u200b \u200b \u200b "
        indent += ">>> "
    for child in group.children:
        group_type = indent
        if child.HasField('group'):
            format_behavior_group_embed(child.group, database, embed, q, indent)
        elif child.HasField('behavior'):
            if group.group_type == 1 or group.group_type == 2 or group.group_type == 9:
                # output += indent + "({})\t".format(GroupType[group.group_type])
                group_type = indent + "({})\t".format(GroupType[group.group_type])
            format_behavior_embed(child.behavior, database, embed, group_type, q, indent)


# return output

# Format:
# Skill Name    Type:Preemptive/Passive/Etc
# Skill Effect
# Condition
def format_monster_embed(mb: MonsterBehavior, q: dict, database: DadguideDatabase, preempt_only: bool = False):
    # output = "Behavior for: {} at Level: {}".format(q["name_en"], q["level"])  # TODO: Delete later after testing
    embed = discord.Embed(title="Behavior for: {} at Level: {}".format(q["name_en"], q["level"]),
                          description="HP:{} ATK:{} DEF:{} TURN:{}".format(q["hp"], q["atk"], q["defence"], q['turns']))
    if mb is None:
        embed.add_field(name="There is no behavior", value="\u200b")
        return embed
    levelBehavior = behaviorForLevel(mb, q["level"])
    if levelBehavior is None:
        embed.add_field(name="There is no behavior", value="\u200b")
        return embed
    for group in levelBehavior.groups:
        format_behavior_group_embed(group, database, embed, q, "", preempt_only)

    return embed


def formatOverview(query):
    output = "Dungeon Name: {}".format(query[0]["dungeon_name_en"])
    for q in query:
        output += "\nEncounter ID: {}   Stage: {}   Monster Name: {}    Level: {}".format(q["encounter_id"], q["stage"],
                                                                                          q["name_en"], q["level"])

    return output


def behaviorForLevel(mb: MonsterBehavior, num: int):
    lev = None
    for level in mb.levels:
        if level.level == num: lev = level
    if lev is None:
        return mb.levels[len(mb.levels) - 1]
    else:
        return lev


class DungeonCog(commands.Cog):
    """My custom cog"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.menu = Menu(bot)
        self.previous_monster_emoji = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}'
        self.previous_page = '\N{BLACK LEFT-POINTING TRIANGLE}'
        self.next_page = '\N{BLACK RIGHT-POINTING TRIANGLE}'
        self.next_monster_emoji = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}'
        self.remove_emoji = self.menu.emoji['no']
        self.next_floor = '\N{UPWARDS BLACK ARROW}'
        self.previous_floor = '\N{DOWNWARDS BLACK ARROW}'
        self.current_monster = '👹'
        self.verbose_monster = '📜'
        self.preempt_monster = '⚡'
        self.esd: EnemySkillDatabase = self.load_raw()

    def load_raw(self):
        urllib.request.urlretrieve(RAW_ENEMY_SKILLS_URL, RAW_ENEMY_SKILLS_DUMP)
        return EnemySkillDatabase(RAW_ENEMY_SKILLS_DUMP)

    def nicknames(self, dungeon_name: str):
        if dungeon_name.lower() in DungeonNickNames:
            return DungeonNickNames[dungeon_name.lower()]
        return None

    def find_difficulty_from_name(self, dungeon_id, sub_name: str, database):
        sub_dungeons = database.database.query_many(sub_dungeons_query.format(dungeon_id, sub_name), ())
        if len(sub_dungeons) == 0:
            return 0
        elif len(sub_dungeons) > 1:
            if 'plus' in sub_name.lower():
                for sd in sub_dungeons:
                    if 'plus' in sd['name_en'].lower():
                        return sd['sub_dungeon_id']
            else:
                for sd in sub_dungeons:
                    if 'plus' not in sd['name_en'].lower():
                        return sd['sub_dungeon_id']
        elif len(sub_dungeons) > 2:
            return 1
        return sub_dungeons[0]['sub_dungeon_id']

    async def find_dungeon_from_name(self, ctx, name: str, database, difficulty: str = None):
        nickname = self.nicknames(name)
        if nickname is not None:
            return nickname
        dungeons = database.database.query_many(dungeon_search_query.format(name), ())
        if len(dungeons) == 0:
            await ctx.send("Sorry, I couldn't find any dungeons by that name! (Or maybe there is no data on it?)")
            return None
        elif len(dungeons) > 1:
            same = True
            first = dungeons[0]["name_en"]
            for d in dungeons:
                if d["name_en"] != first:
                    same = False
                    break
            if not same:
                output = "Can you be more specific? Did you mean:"
                for d in dungeons:
                    output += "\n{}".format(d["name_en"])
                await ctx.send(output)
                return None
        # Now that we have the dungeon we need to get the sub_dungeon_id (difficulty)
        sub_id = dungeons[0]["dungeon_id"] * 1000 + 1
        if difficulty is None:
            sub_id = database.database.query_one(dungeon_sub_id_query.format(dungeons[0]["dungeon_id"]), ())[
                "sub_dungeon_id"]
        elif difficulty.isdigit():
            difficulty = int(difficulty)
            sub_id = dungeons[0]["dungeon_id"] * 1000 + difficulty
            if database.database.query_one(sub_dungeon_exists_query.format(sub_id), ()) is None:
                await ctx.send("That difficulty doesn't exist, following data is for the highest difficulty:")
                sub_id = database.database.query_one(dungeon_sub_id_query.format(dungeons[0]["dungeon_id"]), ())[
                    "sub_dungeon_id"]
        else:
            sub_id = self.find_difficulty_from_name(dungeons[0]['dungeon_id'], difficulty, database)
            if sub_id == 0:
                await ctx.send("Difficulty not found, defaulting to highest difficulty")
                sub_id = database.database.query_one(dungeon_sub_id_query.format(dungeons[0]["dungeon_id"]), ())[
                    "sub_dungeon_id"]
            elif sub_id == 1:
                await ctx.send("Can you be more specific?")
                return None
        return sub_id

    """
    Process_[behavior, behavior_group, monster]: These functions take the behavior data and convert it to a easier to work
    (for me) objects
    """

    async def process_behavior(self, behavior: Behavior, database, q: dict, parent: GroupedSkills = None):
        skill = database.database.query_one(skill_query.format(behavior.enemy_skill_id), ())
        if skill is None:
            return "Unknown"
        skill_name = skill["name_en"]
        skill_effect = skill["desc_en"]
        # skill_processed_text = process_enemy_skill(skill_effect, q, skill)
        es = self.esd.get_es_from_id(skill['enemy_skill_id'])
        skill_processed_text = process_enemy_skill2(q, skill, es, self.esd)
        es_raw = [es]
        if es.type in (83, 95):
            for s in list(filter(None, es.params[1:11])):
                es_raw.append(self.esd.get_es_from_id(s))

        condition = format_condition(behavior.condition)
        processed_skill: ProcessedSkill = ProcessedSkill(skill_name, skill_effect, skill_processed_text, condition,
                                                         parent, es_raw)
        # embed.add_field(name="{}Skill Name: {}{}".format(group_type, skill_name, process_enemy_skill(skill_effect, q, skill)), value="{}Effect: {}\n{}".format(indent, skill_effect, condition), inline=False)
        return processed_skill

    async def process_behavior_group(self, group: BehaviorGroup, database, q: dict,
                                     parent: GroupedSkills = None):
        condition = format_condition(group.condition)
        processed_group: GroupedSkills = GroupedSkills(condition, GroupType[group.group_type], parent)
        for child in group.children:
            if child.HasField('group'):
                processed_group.add_group(await self.process_behavior_group(child.group, database, q, processed_group))
            elif child.HasField('behavior'):
                processed_group.add_skill(await self.process_behavior(child.behavior, database, q, processed_group))
        return processed_group

    # return output

    # Format:
    # Skill Name    Type:Preemptive/Passive/Etc
    # Skill Effect
    # Condition
    async def process_monster(self, mb: MonsterBehavior, q: dict, database: DadguideDatabase):
        # output = "Behavior for: {} at Level: {}".format(q["name_en"], q["level"])  # TODO: Delete later after testing
        """embed = discord.Embed(title="Behavior for: {} at Level: {}".format(q["name_en"], q["level"]),
                              description="HP:{} ATK:{} DEF:{} TURN:{}".format(q["hp"], q["atk"], q["defence"], q['turns']))"""
        monster: ProcessedMonster = ProcessedMonster(q["name_en"], q['hp'], q['atk'], q['defence'], q['turns'],
                                                     q['level'])
        if mb is None:
            return monster
        levelBehavior = behaviorForLevel(mb, q["level"])
        if levelBehavior is None:
            return monster
        for group in levelBehavior.groups:
            monster.add_group(await self.process_behavior_group(group, database, q))

        return monster

    async def make_emoji_dictionary(self, ctx, pm: ProcessedMonster = None, scroll_monsters=None, scroll_floors=None,
                                    floor_info: "list[int]" = None, dungeon_info: "list[int]" = None,
                                    technical: int = None):
        if scroll_monsters is None:
            scroll_monsters = []
        if scroll_floors is None:
            scroll_floors = []
        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.current_monster] = await pm.make_embed(spawn=floor_info, floor=dungeon_info,
                                                                   technical=technical)
        emoji_to_embed[self.verbose_monster] = await pm.make_embed(verbose=True, spawn=floor_info, floor=dungeon_info,
                                                                   technical=technical)
        emoji_to_embed[self.preempt_monster] = await pm.make_preempt_embed(spawn=floor_info, floor=dungeon_info,
                                                                           technical=technical)
        emoji_to_embed[self.previous_monster_emoji] = None
        emoji_to_embed[self.next_monster_emoji] = None
        emoji_to_embed[self.previous_floor] = None
        emoji_to_embed[self.next_floor] = None

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
    async def encounter_info(self, ctx, query: str, new: bool = False):
        """Spits out encounter information for a monster"""
        dg_cog = self.bot.get_cog('Dadguide')
        # Your code will go here
        if not dg_cog:
            logger.warning("Cog 'Dadguide' not loaded")
            return
        logger.info('Waiting until DG is ready')
        await dg_cog.wait_until_ready()
        # sub_id = 4301003
        test_result = dg_cog.database.database.query_one(encounter_query.format(query), ())
        behavior_test = MonsterBehavior()
        behavior_test.ParseFromString(test_result["behavior"])

        # await ctx.send(formatOverview(test_result))
        if new:
            monster = await self.process_monster(behavior_test, test_result, dg_cog.database)
            await ctx.send(embed=await monster.make_embed(verbose=True))
        else:
            await ctx.send(embed=format_monster_embed(behavior_test, test_result, dg_cog.database))

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
        sub_id = await self.find_dungeon_from_name(ctx=ctx, name=name, database=dg_cog.database, difficulty=difficulty)
        if sub_id is None:
            return
        test_result = dg_cog.database.database.query_many(dungeon_query.format(sub_id), ())
        if test_result is None:
            await ctx.send("Dungeon not Found")
        else:
            # await ctx.send(formatOverview(test_result))
            current_stage = 0
            pm_dungeon = []
            # check for invades:
            invades = []
            for r in test_result:
                enc = dg_cog.database.database.query_one(encounter_query.format(r["encounter_id"]), ())
                behavior_test = MonsterBehavior()
                if enc["behavior"] is not None:
                    behavior_test.ParseFromString(enc["behavior"])
                else:
                    behavior_test = None

                # await ctx.send(formatOverview(test_result))
                pm = await self.process_monster(behavior_test, enc, dg_cog.database)
                if r['stage'] < 0:
                    pm.am_invade = True
                    invades.append(pm)
                elif r['stage'] > current_stage:
                    current_stage = r['stage']
                    floor = [pm]
                    pm_dungeon.append(floor)
                else:
                    pm_dungeon[current_stage - 1].append(pm)
            for f in pm_dungeon:
                if pm_dungeon.index(f) != (len(pm_dungeon) - 1):
                    f.extend(invades)
            emoji_to_embed = await self.make_emoji_dictionary(ctx, pm_dungeon[0][0], floor_info=[1, len(pm_dungeon[0])],
                                                              dungeon_info=[1, len(pm_dungeon)],
                                                              technical=int(test_result[0]['technical']))
            dmu = DungeonEmojiUpdater(ctx, emoji_to_embed, self, start_selection[starting], pm_dungeon[0][0],
                                      pm_dungeon, pm_dungeon[0], technical=test_result[0]['technical'])
            await self._do_menu(ctx, start_selection[starting], dmu, 60)

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

    @commands.command()
    async def weather_warning(self, ctx, name: str, difficulty: str = None):
        '''
        Lists all of the preempt hazards/passives of a dungeon
        Name: Name of Dungeon
        Difficulty: Default to the highest difficulty
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
        sub_id = await self.find_dungeon_from_name(ctx=ctx, name=name, database=dg_cog.database, difficulty=difficulty)
        if sub_id is None:
            return
        test_result = dg_cog.database.database.query_many(dungeon_query.format(sub_id), ())
        if test_result is None:
            await ctx.send("Dungeon not Found")
        else:
            # await ctx.send(formatOverview(test_result))
            current_stage = 0
            pm_dungeon = []
            for r in test_result:
                enc = dg_cog.database.database.query_one(encounter_query.format(r["encounter_id"]), ())
                behavior_test = MonsterBehavior()
                if enc["behavior"] is not None:
                    behavior_test.ParseFromString(enc["behavior"])
                else:
                    behavior_test = None

                # await ctx.send(formatOverview(test_result))
                pm = await self.process_monster(behavior_test, enc, dg_cog.database)
                if r['stage'] > current_stage:
                    current_stage = r['stage']
                    floor = [pm]
                    pm_dungeon.append(floor)
                else:
                    pm_dungeon[current_stage - 1].append(pm)
        skills = []
        # array of params for a table of hell:
        # [[resolves], [debuffs], Absurd Preempt Damage, awoken bind, regular bind, skill delay,[hazard emojis], [skyfall hazard emojis], fucks with leader,
        # unmatchables, [skyfalls]]

        idk = []
        idk.append("Preemptives for {}:{}".format(test_result[0]['dungeon_name_en'], test_result[0]['sub_name_en']))
        for f in pm_dungeon:
            floor_skills = []
            for m in f:
                monster_dangers = await self.danger_skill_checker_simple(await m.collect_skills())
                floor_skills.append(''.join(monster_dangers))
            idk.append("Floor {}: {}".format((pm_dungeon.index(f) + 1), '\t'.join(floor_skills)))

        """df = pd.DataFrame(idk, columns=['Resolves', 'Debuffs', 'Attack', 'A. Bind'])
        browser = await launch()
        page = await browser.newPage()
        await page.setContent(df.to_html())
        img = BytesIO(await page.screenshot())
        img.seek(0)
        await ctx.send('Test', file=discord.File(img, filename='test.png'))"""
        for page in pagify("\n".join(idk)):
            await ctx.send(page)

    async def danger_skill_checker(self, skills: List[ProcessedSkill]):
        resolves = set()
        debuffs = set()
        absurd_preempt = 'Maybe Later'
        awoken_bind = set()
        regular_bind = set()
        skill_delay = set()
        hazards = set()
        skyfalls = set()
        leader_fuck = set()
        unmatchables = set()
        skyfalls = set()
        for s in skills:
            for es_raw in s.es_raw:
                if s.is_passive_preempt:
                    if es_raw.type == 73:
                        resolves.add(emoji_dict['resolve'])
                    elif es_raw.type == 129:
                        resolves.add(emoji_dict['super_resolve'])
                    elif es_raw.type == 39:
                        debuffs.add(emoji_dict['time_debuff'])
                    elif es_raw.type == 105:
                        debuffs.add(emoji_dict['rcv_debuff'] if emoji_dict['rcv_debuff'] in s.processed else emoji_dict[
                            'rcv_buff'])
                    elif es_raw.type == 130:
                        debuffs.add(emoji_dict['atk_debuff'])
                    elif es_raw.type == 88:
                        awoken_bind.add(emoji_dict['awoken_bind'])
        ret = [''.join(resolves), ''.join(debuffs), absurd_preempt, ''.join(awoken_bind)]
        return ret

    async def danger_skill_checker_simple(self, skills: List[ProcessedSkill]):
        ret = []
        for s in skills:
            if s.is_passive_preempt:
                ret.append(s.processed)
        return ret


"""
"list all hazard resist that appears in dg
.... as preempt
.... at all"
"""
