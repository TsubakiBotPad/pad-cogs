from collections import OrderedDict
from typing import List
import discord

from dadguide.models.encounter_model import EncounterModel
from dadguide.models.enemy_skill_model import EnemySkillModel
from dungeon.models.EnemySkill import EnemySkill, ESNone

emoji_dict ={
    '{}': '',
}

emoji_dict_old = {
    'recover': "{recover_health}",
    'roulette': "{roulette}",
    'unknown': "{unknown_type}",
    'defense': "{defense_status}",
    'defense25': "{defense25_status}",
    'defense50': "{defense50_status}",
    'defense75': "{defense75_status}",
    'defense80': "{defense80_status}",
    'defense90': "{defense90_status}",
    'defense95': "{defense95_status}",
    'defense99': "{defense99_status}",
    'combo_absorb': "{combo_absorb_status}️",
    'absorb': "{absorb_status}",
    'damage_absorb': "{damage_absorb_status}",
    'void': "{damage_void_status}",
    'status_shield': "{status_shield_status}",
    'resolve': "{resolve_status}",
    'rcv_buff': "{recover_buff_status}️",
    'atk_debuff': "{attack_debuff_status}",
    'rcv_debuff': "{recover_debuff_status}",
    'movetime_buff': "{movetime_buff_status}",
    'movetime_debuff': "{movetime_debuff_status}",
    'dispel': "{dispel_status}",
    'swap': "{leader_swap_status}",
    'skill_delay': '{skill_delay}',
    'locked': '{lock_orbs}',
    'tape': '{tape_status}',
    'starting_position': '{fixed_start}',
    'cloud': '{cloud_status}',
    'gravity': '{gravity}',
    'invincible': '{invincible_status}',
    'invincible_off': '{invincible_off_status}',
    'force_target': '{force_target_status}',
    'leader_alter': '{leader_alter_status}',
    'board_size': '{board_size_status}',
    'super_resolve': '{super_resolve_status}',
    'turn_change': '{turn_change}',
    'enrage': '{enrage_status}',
    'skill_bind': '{skill_bind}',
    'do_nothing': '{do_nothing}',
    'awoken_bind': '{awoken_bind}',
    'no_skyfall': '{no_skyfall_status}',
    'bind': "{bind}",
    'skyfall': '{skyfall_status}',
    'blind': "{blind}",
    'super_blind': "{super_blind}",
    'to': "{to}",
    'attack': '{attack}',
    'multi_attack': '{multi_attack}',
    'self': '{target_self}',
    'health': '{health}',
    'combo': '{combo_orb}'
}

# This is the 3rd dictionary
_ATTRS = {
    -9: '{locked_bomb_orb}',
    -1: '{random_attribute}',
    None: '{fire_orb}',
    0: '{fire_orb}',
    1: '{water_orb}',
    2: '{wood_orb}',
    3: '{light_orb}',
    4: '{dark_orb}',
    5: '{healer_orb}',
    6: '{jammer_orb}',
    7: '{poison_orb}',
    8: '{mortal_poison_orb}',
    9: '{bomb_orb}',
}
# This is the 4th
_TYPES = {
    0: '{evo_material_type}',
    1: '{balanced_type}',
    2: '{physical_type}',
    3: '{healer_type}',
    4: '{dragon_type}',
    5: '{god_type}',
    6: '{attacker_type}',
    7: '{devil_type}',
    8: '{machine_type}',
    12: '{awakening_material_type}',
    14: '{enhance_material_type}',
    15: '{redeemable_material_type}',
}

