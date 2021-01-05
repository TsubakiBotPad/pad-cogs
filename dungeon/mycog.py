import logging

from redbot.core import commands

from google.protobuf import text_format

from dadguide import DadguideDatabase, database_manager
from dungeon.enemy_skills_pb2 import MonsterBehavior, LevelBehavior, BehaviorGroup, Condition, Behavior

logger = logging.getLogger('red.padbot-cogs.padinfo')

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
encounters.*,
enemy_data.behavior
FROM
encounters
LEFT OUTER JOIN dungeons ON encounters.dungeon_id = dungeons.dungeon_id
LEFT OUTER JOIN enemy_data ON encounters.enemy_id = enemy_data.enemy_id
LEFT OUTER JOIN monsters ON encounters.monster_id = monsters.monster_id
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

encounter_query = '''
SELECT
monsters.name_en,
encounters.*,
enemy_data.behavior
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


# From pad-data-pipeline
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

def format_behavior(behavior: Behavior, database):
    output = ""
    skill = database.database.query_one(skill_query.format(behavior.enemy_skill_id), ())
    if skill is None:
        return "Unknown"
    skill_name = skill["name_en"]
    skill_effect = skill["desc_en"]
    output += '\tSkill Name: ' + skill_name
    output += '\nEffect: ' + skill_effect
    return output

def format_behavior_group(group: BehaviorGroup, database: DadguideDatabase):
    output = ""
    condition = format_condition(group.condition)
    if condition is not None:
        output += "\nCondition: {}".format(condition)
    for child in group.children:
        if child.HasField('group'):
            output += format_behavior_group(child.group, database)
        elif child.HasField('behavior'):
            output += "\n({})".format(GroupType[group.group_type])
            output += format_behavior(child.behavior, database)
    return output

# Format:
# Skill Name    Type:Preemptive/Passive/Etc
# Skill Effect
# Condition
def format_monster(mb: MonsterBehavior, q: dict, database: DadguideDatabase):
    output = "Behavior for: {} at Level: {}".format(q["name_en"], q["level"])  # TODO: Delete later after testing
    if mb is None:
        output += "\n There is no Behavior"
        return output
    levelBehavior = behaviorForLevel(mb, q["level"])
    if levelBehavior is None:
        return "Something Broke"
    for group in levelBehavior.groups:
        output += format_behavior_group(group, database)
    return output


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


class Mycog(commands.Cog):
    """My custom cog"""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    @commands.command()
    async def encounter_info(self, ctx, query: str):
        """This does stuff!"""
        dg_cog = self.bot.get_cog('Dadguide')
        # Your code will go here
        if not dg_cog:
            logger.warning("Cog 'Dadguide' not loaded")
            return
        logger.info('Waiting until DG is ready')
        await dg_cog.wait_until_ready()
        #sub_id = 4301003
        test_result = dg_cog.database.database.query_one(encounter_query.format(query), ())
        behavior_test = MonsterBehavior()
        behavior_test.ParseFromString(test_result["behavior"])

        #await ctx.send(formatOverview(test_result))
        await ctx.send(format_monster(behavior_test, test_result, dg_cog.database))
        # await ctx.send(text_format.MessageToString(1, as_utf8=True, indent = 2))
        # await ctx.send(behavior_test.levels[0].level == 2)


    @commands.command()
    async def dungeon_info(self, ctx, name: str, difficulty: int = -1):
        dg_cog = self.bot.get_cog('Dadguide')
        if not dg_cog:
            logger.warning("Cog 'Dadguide' not loaded")
            return
        logger.info('Waiting until DG is ready')
        await dg_cog.wait_until_ready()

        dungeons = dg_cog.database.database.query_many(dungeon_search_query.format(name), ())
        if len(dungeons) == 0:
            await ctx.send("Sorry, I couldn't find any dungeons by that name! (Or maybe there is no data on it?)")
            return
        elif len(dungeons) > 1:
            output = "Can you be more specific? Did you mean:"
            for d in dungeons:
                output += "\n{}".format(d["name_en"])
            await ctx.send(output)
            return
        # Now that we have the dungeon we need to get he sub_dungeon_id (difficulty)
        sub_id = dungeons[0]["dungeon_id"] * 1000 + difficulty
        if difficulty == -1:
            sub_id = dg_cog.database.database.query_one(dungeon_sub_id_query.format(dungeons[0]["dungeon_id"]), ())[
                "sub_dungeon_id"]
        elif dg_cog.database.database.query_one(sub_dungeon_exists_query.format(sub_id), ()) is None:
            await ctx.send("That difficulty doesn't exist, following data is for the highest difficulty:")
            sub_id = dg_cog.database.database.query_one(dungeon_sub_id_query.format(dungeons[0]["dungeon_id"]), ())[
                "sub_dungeon_id"]

        test_result = dg_cog.database.database.query_many(dungeon_query.format(sub_id), ())
        if test_result is None:
            await ctx.send("Dungeon not Found")
        else:
            await ctx.send(formatOverview(test_result))

    # For Tsubakibot devs: If this ever gets merged delete this command
    @commands.command()
    async def dungeon_vomit(self, ctx, name: str, difficulty: int = -1):
        dg_cog = self.bot.get_cog('Dadguide')
        if not dg_cog:
            logger.warning("Cog 'Dadguide' not loaded")
            return
        logger.info('Waiting until DG is ready')
        await dg_cog.wait_until_ready()

        dungeons = dg_cog.database.database.query_many(dungeon_search_query.format(name), ())
        if len(dungeons) == 0:
            await ctx.send("Sorry, I couldn't find any dungeons by that name! (Or maybe there is no data on it?)")
            return
        elif len(dungeons) > 1:
            output = "Can you be more specific? Did you mean:"
            for d in dungeons:
                output += "\n{}".format(d["name_en"])
            await ctx.send(output)
            return
        # Now that we have the dungeon we need to get he sub_dungeon_id (difficulty)
        sub_id = dungeons[0]["dungeon_id"] * 1000 + difficulty
        if difficulty == -1:
            sub_id = dg_cog.database.database.query_one(dungeon_sub_id_query.format(dungeons[0]["dungeon_id"]), ())[
                "sub_dungeon_id"]
        elif dg_cog.database.database.query_one(sub_dungeon_exists_query.format(sub_id), ()) is None:
            await ctx.send("That difficulty doesn't exist, following data is for the highest difficulty:")
            sub_id = dg_cog.database.database.query_one(dungeon_sub_id_query.format(dungeons[0]["dungeon_id"]), ())[
                "sub_dungeon_id"]

        test_result = dg_cog.database.database.query_many(dungeon_query.format(sub_id), ())
        if test_result is None:
            await ctx.send("Dungeon not Found")
        else:
            # await ctx.send(formatOverview(test_result))
            for r in test_result:
                enc = dg_cog.database.database.query_one(encounter_query.format(r["encounter_id"]), ())
                behavior_test = MonsterBehavior()
                if enc["behavior"] is not None:
                    behavior_test.ParseFromString(enc["behavior"])
                else:
                    behavior_test = None

                # await ctx.send(formatOverview(test_result))
                await ctx.send(format_monster(behavior_test, enc, dg_cog.database))