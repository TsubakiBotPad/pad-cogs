from discordmenu.emoji.emoji_cache import emoji_cache

from dbcog.database_context import DbContext
from dbcog.models.encounter_model import EncounterModel
from dbcog.models.enemy_skill_model import EnemySkillModel
from dungeon.safe_dict import SafeDict
from dungeon.dungeon_monster import DungeonMonster
from dungeon.enemy_skill import ProcessedSkill
from dungeon.enemy_skills_pb2 import Condition, MonsterBehavior, Behavior, BehaviorGroup
from dungeon.grouped_skillls import GroupedSkills

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


def process_enemy_skill2(encounter: EncounterModel, skill: EnemySkillModel, emoji_map):
    effect = skill.desc_en_emoji
    split_effects = effect.split("), ")
    non_attack_effects = []
    for e in split_effects:
        # print(encounter.monster_id)
        e += ")"
        if "Attack:" not in e:
            non_attack_effects.append(e.format_map(emoji_map))

    # Damage
    atk = encounter.atk
    if skill.min_hits != 0:
        emoji = emoji_map['attack']
        if skill.min_hits > 1:
            emoji = emoji_map['multi_attack']
        damage_per_hit = (int)(atk * (skill.atk_mult / 100.0))
        min_damage = skill.min_hits * damage_per_hit
        max_damage = skill.max_hits * damage_per_hit
        if min_damage != max_damage:
            non_attack_effects.append("({}:{}~{})".format(emoji, f'{min_damage:,}', f'{max_damage:,}'))
        else:
            non_attack_effects.append("({}:{})".format(emoji, f'{min_damage:,}'))

    return non_attack_effects


"""
Process_[behavior, behavior_group, monster]: These functions take the behavior data and convert it to a easier to work
(for me) objects
"""


def process_behavior(behavior: Behavior, database, q: EncounterModel, emoji_map, parent: GroupedSkills = None):
    skill = database.dungeon.get_enemy_skill(behavior.enemy_skill_id)
    if skill is None:
        return "Unknown"
    skill_name = skill.name_en
    skill_effect = skill.desc_en
    # skill_processed_text = process_enemy_skill(skill_effect, q, skill)
    skill_processed_texts = process_enemy_skill2(q, skill, emoji_map)

    condition = format_condition(behavior.condition)
    processed_skill: ProcessedSkill = ProcessedSkill(skill_name, skill_effect, skill_processed_texts, condition,
                                                     parent)
    # embed.add_field(name="{}Skill Name: {}{}".format(group_type, skill_name, process_enemy_skill(skill_effect, q, skill)), value="{}Effect: {}\n{}".format(indent, skill_effect, condition), inline=False)
    return processed_skill


def process_behavior_group(group: BehaviorGroup, database, q: EncounterModel, emoji_map,
                           parent: GroupedSkills = None):
    condition = format_condition(group.condition)
    processed_group: GroupedSkills = GroupedSkills(condition, GroupType[group.group_type], parent)
    for child in group.children:
        if child.HasField('group'):
            processed_group.add_group(process_behavior_group(child.group, database, q, emoji_map, processed_group))
        elif child.HasField('behavior'):
            processed_group.add_skill(process_behavior(child.behavior, database, q, emoji_map, processed_group))
    return processed_group


# return output

# Format:
# Skill Name    Type:Preemptive/Passive/Etc
# Skill Effect
# Condition
def process_monster(mb: MonsterBehavior, q: EncounterModel, database: DbContext):
    # output = "Behavior for: {} at Level: {}".format(q["name_en"], q["level"])  # TODO: Delete later after testing
    """embed = discord.Embed(title="Behavior for: {} at Level: {}".format(q["name_en"], q["level"]),
                          description="HP:{} ATK:{} DEF:{} TURN:{}".format(q["hp"], q["atk"], q["defence"], q['turns']))"""
    emoji_map = SafeDict(resolve_status=emoji_cache.get_by_name('resolve'),
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
                         awoken_skill_bind=emoji_cache.get_by_name('awoken_skill_bind'),
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
                         random_attribute='[Random Att]',
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
                         redeemable_material_type='🪙',
                         no_match_fire=emoji_cache.get_by_name('no_match_fire'),
                         no_match_wood=emoji_cache.get_by_name('no_match_wood'),
                         no_match_water=emoji_cache.get_by_name('no_match_water'),
                         no_match_dark=emoji_cache.get_by_name('no_match_dark'),
                         no_match_light=emoji_cache.get_by_name('no_match_light'),
                         no_match_heart=emoji_cache.get_by_name('no_match_heart'),
                         no_match_jammer=emoji_cache.get_by_name('no_match_jammer'),
                         no_match_poison=emoji_cache.get_by_name('no_match_poison'),
                         no_match_heal=emoji_cache.get_by_name('no_match_heal'),
                         recover_debuff_status=emoji_cache.get_by_name('recover_debuff_status'),
                         attack_debuff_status='⚔️''⬇️'
                         )
    monster_model = database.graph.get_monster(q.monster_id)
    monster: DungeonMonster = DungeonMonster(
        name=monster_model.name_en,
        hp=q.hp,
        atk=q.atk,
        defense=q.defence,
        turns=q.turns,
        level=q.level
    )
    if mb is None:
        return monster
    levelBehavior = behaviorForLevel(mb, q.level)
    if levelBehavior is None:
        return monster
    for group in levelBehavior.groups:
        monster.add_group(process_behavior_group(group, database, q, emoji_map))

    return monster
