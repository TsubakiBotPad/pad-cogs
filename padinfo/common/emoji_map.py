from enum import Enum
from typing import Union, Optional, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel
    from dadguide.models.enum_types import AwakeningRestrictedLatent, MonsterType

from discordmenu.emoji.emoji_cache import emoji_cache

AWAKENING_ID_TO_EMOJI_NAME_MAP = {
    1: 'boost_hp',
    2: 'boost_atk',
    3: 'boost_rcv',
    4: 'reduce_fire',
    5: 'reduce_water',
    6: 'reduce_wood',
    7: 'reduce_light',
    8: 'reduce_dark',
    9: 'misc_autoheal',
    10: 'res_bind',
    11: 'res_blind',
    12: 'res_jammer',
    13: 'res_poison',
    14: 'oe_fire',
    15: 'oe_water',
    16: 'oe_wood',
    17: 'oe_light',
    18: 'oe_dark',
    19: 'misc_te',
    20: 'misc_bindclear',
    21: 'misc_sb',
    22: 'row_fire',
    23: 'row_water',
    24: 'row_wood',
    25: 'row_light',
    26: 'row_dark',
    27: 'misc_tpa',
    28: 'res_skillbind',
    29: 'oe_heart',
    30: 'misc_multiboost',
    31: 'killer_dragon',
    32: 'killer_god',
    33: 'killer_devil',
    34: 'killer_machine',
    35: 'killer_balance',
    36: 'killer_attacker',
    37: 'killer_physical',
    38: 'killer_healer',
    39: 'killer_evomat',
    40: 'killer_awoken',
    41: 'killer_enhancemat',
    42: 'killer_vendor',
    43: 'misc_comboboost',
    44: 'misc_guardbreak',
    45: 'misc_extraattack',
    46: 'teamboost_hp',
    47: 'teamboost_rcv',
    48: 'misc_voidshield',
    49: 'misc_assist',
    50: 'misc_super_extraattack',
    51: 'misc_skillcharge',
    52: 'res_bind_super',
    53: 'misc_te_super',
    54: 'res_cloud',
    55: 'res_seal',
    56: 'misc_sb_super',
    57: 'attack_boost_high',
    58: 'attack_boost_low',
    59: 'l_shield',
    60: 'l_attack',
    61: 'misc_super_comboboost',
    62: 'orb_combo',
    63: 'misc_voice',
    64: 'misc_dungeonbonus',
    65: 'reduce_hp',
    66: 'reduce_atk',
    67: 'reduce_rcv',
    68: 'res_blind_super',
    69: 'res_jammer_super',
    70: 'res_poison_super',
    71: 'misc_jammerboost',
    72: 'misc_poisonboost',
    73: 'cc_fire',
    74: 'cc_water',
    75: 'cc_wood',
    76: 'cc_light',
    77: 'cc_dark',
    78: 'cross_attack',
}

AWAKENING_RESTRICTED_LATENT_VALUE_TO_EMOJI_NAME_MAP = {
    606: 'unmatchable_clear',
    607: 'spinner_clear',
    608: 'absorb_pierce',
}


def awakening_restricted_latent_emoji(latent: "AwakeningRestrictedLatent"):
    return get_emoji('latent_{}'.format(AWAKENING_RESTRICTED_LATENT_VALUE_TO_EMOJI_NAME_MAP[latent.value]))


def get_type_emoji(mons_type: "MonsterType"):
    return get_emoji('mons_type_' + mons_type.name.lower())


def get_attribute_emoji_by_monster(monster: "MonsterModel"):
    attr1 = monster.attr1.name.lower()
    attr2 = monster.attr2.name.lower()
    emoji = "{}_{}".format(attr1, attr2) if attr1 != attr2 else 'orb_{}'.format(attr1)
    return get_emoji(emoji)


def get_attribute_emoji_by_enum(type1: Union[Enum, Literal[False]], type2: Optional[Union[Enum, Literal[bool]]] = None):
    attr1 = 'nil' if type1 is False else type1.name.lower()
    attr2 = 'nil' if type2 is False else type2.name.lower() if type2 else attr1
    emoji = "{}_{}".format(attr1, attr2) if attr1 != attr2 else 'orb_{}'.format(attr1)
    return get_emoji(emoji)


def get_rarity_emoji(rarity: int):
    emoji = 'star_0{}'.format(rarity) if rarity < 10 else 'star_{}'.format(rarity)
    return get_emoji(emoji)


def get_awakening_emoji(awid: Union[Enum, int], default: str = None):
    return get_emoji(AWAKENING_ID_TO_EMOJI_NAME_MAP.get(awid if isinstance(awid, int) else awid.value, default))


def get_emoji(name):
    if isinstance(name, int):
        name = AWAKENING_ID_TO_EMOJI_NAME_MAP[name]
    return emoji_cache.get_emoji(name)
