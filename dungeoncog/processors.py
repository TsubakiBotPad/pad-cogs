import re
from typing import Optional, TYPE_CHECKING

from discordmenu.emoji.emoji_cache import emoji_cache
from tsutils.enums import Server

from dungeoncog.dungeon_monster import DungeonMonster
from dungeoncog.enemy_skill import ProcessedSkill
from dungeoncog.enemy_skills_pb2 import Behavior, BehaviorGroup, Condition, MonsterBehavior
from dungeoncog.grouped_skillls import GroupedSkills

if TYPE_CHECKING:
    from dbcog.models.enemy_skill_model import EnemySkillModel
    from dbcog.database_context import DbContext
    from dbcog.models.encounter_model import EncounterModel

    
DEFAULT_SERVER = Server.COMBINED
    
GROUP_TYPES = {
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


def format_condition(cond: Condition) -> Optional[str]:
    parts = []
    if cond.skill_set:
        parts.append(f"SkillSet {cond.skill_set}")
    if cond.use_chance not in [0, 100]:
        parts.append(f"{cond.use_chance}% chance")
    if cond.global_one_time:
        parts.append(f"one time only")
    if cond.limited_execution:
        parts.append(f"at most {cond.limited_execution} times")
    if cond.trigger_enemies_remaining:
        parts.append(f"when {cond.trigger_enemies_remaining} enemies remain")
    if cond.if_defeated:
        parts.append(f"when defeated")
    if cond.if_attributes_available:
        parts.append(f"when required attributes on board")
    if cond.trigger_monsters:
        parts.append(f"when {', '.join(map(str, cond.trigger_monsters))} on team")
    if cond.trigger_combos:
        parts.append(f"when {cond.trigger_combos} combos last turn")
    if cond.if_nothing_matched:
        parts.append(f"if no other skills matched")
    if cond.repeats_every:
        if cond.trigger_turn:
            if cond.trigger_turn_end:
                parts.append(f"turns {cond.trigger_turn}-{cond.trigger_turn_end} of every {cond.repeats_every} turns")
            else:
                parts.append(f"turn {cond.trigger_turn} of every {cond.repeats_every} turns")
        else:
            parts.append(f"repeats every {cond.repeats_every} turns")
    elif cond.trigger_turn_end:
        turn_text = f"turns {cond.trigger_turn}-{cond.trigger_turn_end}"
        parts.append(_cond_hp_timed_text(cond.always_trigger_above, turn_text))
    elif cond.trigger_turn:
        turn_text = f"turn {cond.trigger_turn}"
        parts.append(_cond_hp_timed_text(cond.always_trigger_above, turn_text))

    if cond.hp_threshold == 101:
        parts.append(f"when HP is full")
    elif cond.hp_threshold not in (100, 0):
        parts.append(f"HP <= {cond.hp_threshold}")

    return ', '.join(parts) or None


# From pad-data-pipeline
def _cond_hp_timed_text(always_trigger_above: int, turn_text: str) -> str:
    text = turn_text
    if always_trigger_above == 1:
        text = f"always {turn_text}"
    elif always_trigger_above:
        text = f"{turn_text} while HP > {always_trigger_above}"
    return text


def format_overview(query):
    output = f"Dungeon Name: {query[0]['dungeon_name_en']}"
    for q in query:
        output += f"\nEncounter ID: {q['encounter_id']}   Stage: {q['stage']}   Monster Name: {q['name_en']}"
    return output


def behavior_for_level(behavior: MonsterBehavior, num: int):
    lev = None
    for level in behavior.levels:
        if level.level == num:
            lev = level
    if lev is None:
        return behavior.levels[len(behavior.levels) - 1]
    else:
        return lev


def process_enemy_skill(encounter: "EncounterModel", skill: "EnemySkillModel", emoji_map):
    non_attack_effects = []
    for e in re.split(r'(?<=\)), ', skill.desc_en_emoji):
        if "Attack:" not in e:
            non_attack_effects.append(e.format_map(emoji_map))

    # Damage
    atk = encounter.atk
    if skill.min_hits != 0:
        emoji = emoji_map['attack']
        if skill.min_hits > 1:
            emoji = emoji_map['multi_attack']
        damage_per_hit = int(atk * (skill.atk_mult / 100))
        min_damage = skill.min_hits * damage_per_hit
        max_damage = skill.max_hits * damage_per_hit
        if min_damage != max_damage:
            non_attack_effects.append(f"({emoji}:{min_damage:,}~{max_damage:,})")
        else:
            non_attack_effects.append(f"({emoji}:{min_damage:,})")

    return non_attack_effects


def process_behavior(behavior: Behavior, database, encounter: "EncounterModel", emoji_map,
                     parent: GroupedSkills = None, server: Server = DEFAULT_SERVER):
    skill = database.dungeon.get_enemy_skill(behavior.enemy_skill_id, server=server)
    if skill is None:
        return "Unknown"
    skill_name = skill.name_en
    skill_effect = skill.desc_en
    skill_processed_texts = process_enemy_skill(encounter, skill, emoji_map)

    condition = format_condition(behavior.condition)
    processed_skill: ProcessedSkill = ProcessedSkill(skill_name, skill_effect, skill_processed_texts, condition,
                                                     parent)
    return processed_skill


def process_behavior_group(group: BehaviorGroup, database, encounter: "EncounterModel", emoji_map,
                           parent: GroupedSkills = None):
    condition = format_condition(group.condition)
    processed_group: GroupedSkills = GroupedSkills(condition, GROUP_TYPES[group.group_type], parent)
    for child in group.children:
        if child.HasField('group'):
            processed_group.add_group(
                process_behavior_group(child.group, database, encounter, emoji_map, processed_group))
        elif child.HasField('behavior'):
            processed_group.add_skill(process_behavior(child.behavior, database, encounter, emoji_map, processed_group))
    return processed_group


class SafeDgEmojiDict(dict):
    def __missing__(self, key):
        return '<' + key + '>'


def process_monster(behavior: MonsterBehavior, encounter: "EncounterModel", database: "DbContext") -> DungeonMonster:
    emoji_map = SafeDgEmojiDict(
        resolve_status=emoji_cache.get_by_name('resolve'),
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
        do_nothing='\N{SLEEPING SYMBOL}',
        awoken_skill_bind=emoji_cache.get_by_name('awoken_skill_bind'),
        no_skyfall_status=emoji_cache.get_by_name('no_skyfall'),
        bind=emoji_cache.get_by_name('res_bind'),
        skyfall_status='\N{CLOUD WITH RAIN}',
        blind=emoji_cache.get_by_name('black_circle_real'),
        super_blind=emoji_cache.get_by_name('blind_orb'),
        to='\N{BLACK RIGHTWARDS ARROW}️',
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
        redeemable_material_type='\U0001fa99',  # Coin Emoji
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
        attack_debuff_status='\N{CROSSED SWORDS}\N{DOWNWARDS BLACK ARROW}️'
    )
    monster_model = database.graph.get_monster(encounter.monster_id)
    monster = DungeonMonster(
        hp=encounter.hp,
        atk=encounter.atk,
        defense=encounter.defense,
        turns=encounter.turns,
        level=encounter.level,
        monster=monster_model
    )
    if behavior is None:
        return monster
    level_behavior = behavior_for_level(behavior, encounter.level)
    if level_behavior is None:
        return monster
    for group in level_behavior.groups:
        monster.add_group(process_behavior_group(group, database, encounter, emoji_map))

    return monster
