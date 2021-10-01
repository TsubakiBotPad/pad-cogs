from collections import defaultdict, namedtuple
from enum import Enum
from typing import Mapping, Tuple, TypeVar

from .models.enum_types import Attribute, AwokenSkills, MonsterType

K = TypeVar('K')
V = TypeVar('V')


def inverse_map(token_map: Mapping[K, Tuple[V]]) -> Mapping[V, Tuple[K]]:
    ret = defaultdict(tuple)
    for k, vs in token_map.items():
        for v in vs:
            ret[v] += (k,)
    return ret


COLOR_MAP = {
    Attribute.Fire: ('r', 'red', 'fire'),
    Attribute.Water: ('b', 'blue', 'water'),
    Attribute.Wood: ('g', 'green', 'wood'),
    Attribute.Light: ('l', 'light', 'yellow'),
    Attribute.Dark: ('d', 'dark', 'purple'),
    Attribute.Nil: ('nil', 'x', 'none', 'null', 'white')
}

SUB_COLOR_MAP = {k: tuple('?' + t for t in v if t != "white") for k, v in COLOR_MAP.items()}

DUAL_COLOR_MAP = {}
for cid1, cns1 in COLOR_MAP.items():
    for cid2, cns2 in COLOR_MAP.items():
        _ts = ()
        for t1 in cns1:
            for t2 in cns2:
                if t2 in ("white",):
                    continue
                if len(t1) + len(t2) == 2:
                    _ts += (t1 + t2,)
                if (len(t1) == 1) == (len(t2) == 1):
                    _ts += (t1 + "/" + t2,)
        DUAL_COLOR_MAP[(cid1, cid2)] = _ts

TYPE_MAP = {
    MonsterType.Evolve: ('evolve',),
    MonsterType.Balanced: ('balanced', 'bal', 'balance'),
    MonsterType.Physical: ('physical', 'phys'),
    MonsterType.Healer: ('healer',),
    MonsterType.Dragon: ('dragon', 'dra'),
    MonsterType.God: ('god',),
    MonsterType.Attacker: ('attacker', 'atk'),
    MonsterType.Devil: ('devil', 'dv'),
    MonsterType.Machine: ('machine', 'mech'),
    MonsterType.Awoken: ('awokentype', 'awotype'),
    MonsterType.Enhance: ('enhance', 'fodder', 'enh'),
    MonsterType.Vendor: ('vendor', 'redeemable'),
}


class EvoTypes(Enum):
    BASE = 'Base'
    EVO = 'Evolved'
    UVO = 'Ulimate'
    UUVO = 'Super Ultimate'
    BASETRANS = 'Base Transform'
    TRANS = 'Transform'
    AWOKEN = 'Awoken'
    MEGA = 'Mega Awoken'
    REVO = 'Reincarnated'
    SREVO = 'Super Reincarnated'
    PIXEL = 'Pixel'
    NONPIXEL = 'Nonpixel'


EVO_MAP = {
    EvoTypes.BASE: ('base',),
    EvoTypes.EVO: ('evo', 'evolved'),
    EvoTypes.UVO: ('uvo', 'ult', 'ultimate', 'uevo'),
    EvoTypes.UUVO: ('uuvo', 'uult', 'uultimate', 'uuevo', 'suvo'),
    EvoTypes.BASETRANS: ('transformbase', 'transbase'),
    EvoTypes.TRANS: ('transform', 'trans', 'transformed', 'xf', 'xform', 'tf'),
    EvoTypes.AWOKEN: ('awoken', 'awo', 'a'),
    EvoTypes.MEGA: ('mega', 'mawoken', 'mawo', 'ma', 'megaawoken'),
    EvoTypes.REVO: ('revo', 'reincarnated', 'rv'),
    EvoTypes.SREVO: ('srevo', 'super', 'sr', 'superreincarnated'),
    EvoTypes.PIXEL: ('pixel', 'p', 'dot', 'px'),
    EvoTypes.NONPIXEL: ('nonpixel', 'np'),
}

AWOKEN_SKILL_MAP = {
    AwokenSkills.ENHANCEDHP: ('hp+', 'hp'),
    AwokenSkills.ENHANCEDATK: ('atk+', 'atk'),
    AwokenSkills.ENHANCEDRCV: ('rcv+', 'rcv'),
    AwokenSkills.REDUCERED: ('elresr', 'elres'),  # element resist
    AwokenSkills.REDUCEBLUE: ('elresb', 'elres'),
    AwokenSkills.REDUCEGREEN: ('elresg', 'elres'),
    AwokenSkills.REDUCELIGHT: ('elresl', 'elres'),
    AwokenSkills.REDUCEDARK: ('elresd', 'elres'),
    AwokenSkills.AUTOHEAL: ('autoheal',),
    AwokenSkills.BINDRES: ('unbindable', 'bindres'),
    AwokenSkills.BLINDRES: ('resb', 'bres'),
    AwokenSkills.JAMMERRES: ('resj', 'jres'),
    AwokenSkills.POISONRES: ('resp', 'pres'),
    AwokenSkills.ENHANCEDRED: ('oer', 'oe'),
    AwokenSkills.ENHANCEDBLUE: ('oeb', 'oe'),
    AwokenSkills.ENHANCEDGREEN: ('oeg', 'oe'),
    AwokenSkills.ENHANCEDLIGHT: ('oel', 'oe'),
    AwokenSkills.ENHANCEDDARK: ('oed', 'oe'),
    AwokenSkills.EXTMOVE: ('te', 'finger'),
    AwokenSkills.BINDRECOVERY: ('bindrcv', 'bindclear', 'rowclear'),
    AwokenSkills.SKILLBOOST: ('sb',),
    AwokenSkills.REDROW: ('rowr', 'row'),
    AwokenSkills.BLUEROW: ('rowb', 'row'),
    AwokenSkills.GREENROW: ('rowg', 'row'),
    AwokenSkills.LIGHTROW: ('rowl', 'row'),
    AwokenSkills.DARKROW: ('rowd', 'row'),
    AwokenSkills.TPA: ('tpa', 'pronged'),
    AwokenSkills.SKILLBINDRES: ('sbr',),
    AwokenSkills.ENHANCEDHEAL: ('htpa', 'oeh'),
    AwokenSkills.MULTIBOOST: ('multi', 'mb'),
    AwokenSkills.DRAGONKILLER: ('dragonkiller', 'dk', 'drk', 'killer'),
    AwokenSkills.GODKILLER: ('godkiller', 'gk', 'gok', 'killer'),
    AwokenSkills.DEVILKILLER: ('devilkiller', 'vk', 'dek', 'killer'),
    AwokenSkills.MACHINEKILLER: ('machinekiller', 'mk', 'mak', 'killer'),
    AwokenSkills.BALANCEDKILLER: ('balancedkiller', 'bk', 'bak', 'killer'),
    AwokenSkills.ATTACKERKILLER: ('attackerkiller', 'ak', 'aak', 'killer'),
    AwokenSkills.PHYSICALKILLER: ('physicalkiller', 'pk', 'phk', 'killer'),
    AwokenSkills.HEALERKILLER: ('healerkiller', 'hk', 'hek', 'killer'),
    AwokenSkills.EVOMATKILLER: ('evokiller', 'evok', 'a2killer'),
    AwokenSkills.AWOKENKILLER: ('awokenkiller', 'awok', 'a2killer'),
    AwokenSkills.FODDERKILLER: ('enhancekiller', 'enhk', 'a2killer'),
    AwokenSkills.REDEEMKILLER: ('vendorkiller', 'vendork', 'a2killer'),
    AwokenSkills.ENHCOMBO7C: ('7c',),
    AwokenSkills.GUARDBREAK: ('gb', 'guardbreak'),
    AwokenSkills.FUA: ('fua',),
    AwokenSkills.ENHTEAMHP: ('teamhp', 'thp'),
    AwokenSkills.ENHTEAMRCV: ('teamrcv', 'trcv'),
    AwokenSkills.VDP: ('vdp', 'box'),
    AwokenSkills.EQUIP: ('equip', 'assist', 'eq'),
    AwokenSkills.SUPERFUA: ('sfua',),
    AwokenSkills.SKILLCHARGE: ('rainbowhaste', 'skillcharge', 'hasteawo'),
    AwokenSkills.UNBINDABLE: ('unbindable', 'bindres'),
    AwokenSkills.EXTMOVEPLUS: ('te+', 'te', 'finger+', 'finger'),
    AwokenSkills.CLOUDRESIST: ('cloudres', 'cloud'),
    AwokenSkills.TAPERESIST: ('taperes', 'tape'),
    AwokenSkills.SKILLBOOSTPLUS: ('sb+', 'sb'),
    AwokenSkills.HP80ORMORE: ('>80', 'highhp'),
    AwokenSkills.HP50ORLESS: ('<50', 'lowhp'),
    AwokenSkills.ELSHIELD: ('elshield', 'elh', 'hel'),
    AwokenSkills.ELATTACK: ('el',),
    AwokenSkills.ENHCOMBO10C: ('10c',),
    AwokenSkills.COMBOORB: ('co', 'corb'),
    AwokenSkills.VOICE: ('voice',),
    AwokenSkills.DUNGEONBONUS: ('dgbonus', 'dgboost'),
    AwokenSkills.REDUCEDHP: ('hp-',),
    AwokenSkills.REDUCEDATK: ('atk-',),
    AwokenSkills.REDUCEDRCV: ('rcv-',),
    AwokenSkills.UNBLINDABLE: ('resb+', 'b+',),
    AwokenSkills.UNJAMMABLE: ('resj+', 'j+',),
    AwokenSkills.UNPOISONABLE: ('resp+', 'p+',),
    AwokenSkills.JAMMERBLESSING: ('jblessing', 'sfj', 'jsurge'),
    AwokenSkills.POISONBLESSING: ('pblessing', 'sfp', 'psurge'),
    AwokenSkills.REDCOMBOCOUNT: ('ccr', 'cc'),
    AwokenSkills.BLUECOMBOCOUNT: ('ccb', 'cc'),
    AwokenSkills.GREENCOMBOCOUNT: ('ccg', 'cc'),
    AwokenSkills.LIGHTCOMBOCOUNT: ('ccl', 'cc'),
    AwokenSkills.DARKCOMBOCOUNT: ('ccd', 'cc'),
    AwokenSkills.CROSSATTACK: ('crossattack', 'crossblind'),
    AwokenSkills.ATTR3BOOST: ('attr3', '3attr'),
    AwokenSkills.ATTR4BOOST: ('attr4', '4attr'),
    AwokenSkills.ATTR5BOOST: ('attr5', '5attr'),
}


class MiscModifiers(Enum):
    CHIBI = 'Chibi'
    STORY = 'Story'
    FARMABLE = 'Farmable'
    TRADEABLE = 'Tradeable'
    REM = 'In REM'
    PEM = 'In PEM'
    VEM = 'In VEM'
    MP = 'MP'
    INJP = 'In JP Server'
    ONLYJP = 'Only in JP Server'
    INNA = 'In NA Server'
    ONLYNA = 'Only in NA Server'
    REGULAR = 'Metaseries: REGULAR'
    EVENT = 'Metaseries: Event'
    SEASONAL = 'Metaseries: Seasonal'
    COLLAB = 'Metaseries: Collab'
    NEW = 'Newest monster in series'
    ORBSKIN = 'Grants an orb skin'
    ANIMATED = 'Animated monster'
    MEDAL_EXC = 'Exchangable for vendor mats'
    BLACK_MEDAL = 'Exchangable for black medals'
    CURRENT_EXCHANGE_JP = 'Currently exchangable in JP'
    CURRENT_EXCHANGE_NA = 'Currently exchangable in NA'
    CURRENT_EXCHANGE_KR = 'Currently exchangable in KR'
    PERMANENT_EXCHANGE = 'Permanently exchangable'
    TEMP_EXCHANGE = 'Temporarily exchangable at some point in time'


MISC_MAP = {
    MiscModifiers.CHIBI: ('chibi', 'mini'),
    MiscModifiers.STORY: ('story',),
    MiscModifiers.FARMABLE: ('farmable',),
    MiscModifiers.TRADEABLE: ('tradeable', 'tradable'),
    MiscModifiers.REM: ('rem',),
    MiscModifiers.PEM: ('pem',),
    MiscModifiers.VEM: ('vem', 'adpem'),
    MiscModifiers.MP: ('mp',),
    MiscModifiers.INJP: ('injp',),
    MiscModifiers.INNA: ('inna',),
    MiscModifiers.ONLYJP: ('jp',),
    MiscModifiers.ONLYNA: ('na',),
    MiscModifiers.REGULAR: ('regular',),
    MiscModifiers.EVENT: ('event',),
    MiscModifiers.SEASONAL: ('seasonal',),
    MiscModifiers.COLLAB: ('collab',),
    MiscModifiers.NEW: ('new',),
    MiscModifiers.ORBSKIN: ('orbskin',),
    MiscModifiers.ANIMATED: ('animated',),
    MiscModifiers.MEDAL_EXC: ('medal', 'shop'),
    MiscModifiers.BLACK_MEDAL: ('blackmetal',),
    MiscModifiers.CURRENT_EXCHANGE_JP: ('nowshopjp', 'shopnowjp'),
    MiscModifiers.CURRENT_EXCHANGE_NA: ('nowshopna', 'shopnowna'),
    MiscModifiers.CURRENT_EXCHANGE_KR: ('nowshopkr', 'shopnowkr'),
    MiscModifiers.PERMANENT_EXCHANGE: ('permshop', 'shopperm'),
    MiscModifiers.TEMP_EXCHANGE: ('tempshop', 'shoptemp'),
}

MULTI_WORD_TOKENS = {tuple(ts.split()) for ts in {
    'super reincarnated',
    'mega awoken',
    'orb skin',
    'black metal',
}}

ALL_TOKEN_DICTS = {
    *COLOR_MAP.values(),
    *SUB_COLOR_MAP.values(),
    *DUAL_COLOR_MAP.values(),
    *TYPE_MAP.values(),
    *AWOKEN_SKILL_MAP.values(),
    *EVO_MAP.values(),
    *MISC_MAP.values(),
}

KNOWN_MODIFIERS = {v for vs in ALL_TOKEN_DICTS for v in vs}

COLOR_TOKENS = {
    *sum(COLOR_MAP.values(), ()),
    *sum(SUB_COLOR_MAP.values(), ()),
    *sum(DUAL_COLOR_MAP.values(), ()),
}

AWAKENING_TOKENS = {*sum(AWOKEN_SKILL_MAP.values(), ())}
EVO_TOKENS = {*sum(EVO_MAP.values(), ())}
TYPE_TOKENS = {*sum(TYPE_MAP.values(), ())}

OTHER_HIDDEN_TOKENS = set() \
    .union(COLOR_TOKENS) \
    .union(AWAKENING_TOKENS) \
    .union(EVO_TOKENS) \
    .union(TYPE_TOKENS)

LEGAL_END_TOKENS = {
    "equip",
    "assist",
    "eq",
}

# These tokens have been found to be harmful and will only be added to monsters explicitly.
HAZARDOUS_IN_NAME_MODS = {
    "reincarnated",
    "awoken",
    "equip",
}

PROBLEMATIC_SERIES_TOKENS = {
    "sonia",
    "odin",
    "metatron",
    "kali",
    "fenrir",
    "sherias",
}

ID1_SUPPORTED = {'hw', 'h', 'x', 'ny', 'gh', 'v', 'np', 'ma', 'a', 'r', 'rr', 'rg', 'rb', 'rl', 'rd', 'rx', 'b', 'br',
                 'bg', 'bb', 'bl', 'bd', 'bx', 'g', 'gr', 'gg', 'gb', 'gl', 'gd', 'gx', 'l', 'lr', 'lg', 'lb', 'll',
                 'ld', 'lx', 'd', 'dr', 'dg', 'db', 'dl', 'dd', 'dx', 'x', 'xr', 'xg', 'xb', 'xl', 'xd', 'xx'}

# This probably doesn't belong in here
PlusAwakeningData = namedtuple("PlusAwakeningData", "awoken_skill value")
PLUS_AWOKENSKILL_MAP = {
    AwokenSkills.UNBINDABLE: PlusAwakeningData(AwokenSkills.BINDRES, 2),
    AwokenSkills.EXTMOVEPLUS: PlusAwakeningData(AwokenSkills.EXTMOVE, 2),
    AwokenSkills.SKILLBOOSTPLUS: PlusAwakeningData(AwokenSkills.SKILLBOOST, 2),
}

NUMERIC_MONSTER_ATTRIBUTE_ALIASES = {
    (('monster_no_na',),): ('monsterid', 'monsterno'),
    (('base_evo_id',),): ('baseid',),
    (('superawakening_count',),): ('sacount',),
    (('leader_skill', 'leader_skill_id'),): ('lsid',),
    (('active_skill', 'active_skill_id'),): ('asid',),
    (('series', 'series_id'),): ('sid', 'seriesid'),
    (('rarity',),): ('rarity', 'rare'),
    (('buy_mp',),): ('buymp',),
    (('sell_mp',),): ('sellmp',),
    (('sell_gold',),): ('gold', 'coins'),
    (('cost',),): ('cost', 'teamcost'),
    (('exp',),): ('exp', 'exptomax', 'xptomax'),
    (('fodder_exp',),): ('fodderexp',),
    (('level',),): ('maxlvl', 'maxlevel'),
    (('latent_slots',),): ('latentslots',),
    (('hp_max',),): ('hp', 'maxhp'),
    (('atk_max',),): ('atk', 'maxatk'),
    (('rcv_max',),): ('rcv', 'maxrcv'),
    (('hp_min',),): ('minhp',),
    (('atk_min',),): ('minatk',),
    (('rcv_min',),): ('minrcv',),
}
NUMERIC_MONSTER_ATTRIBUTE_NAMES = {*sum(NUMERIC_MONSTER_ATTRIBUTE_ALIASES.values(), ())}

STRING_MONSTER_ATTRIBUTE_ALIASES = {
    (('name_en',), ('name_ja',)): ('monstername', 'cardname'),
    (('leader_skill', 'name_en'), ('active_skill', 'name_en'),): ('skillname',),
    (('leader_skill', 'desc_en'), ('active_skill', 'desc_en'),): ('skilltext',),
    (('leader_skill', 'name_en'),): ('lsname',),
    (('leader_skill', 'desc_en'),): ('lsdesc',),
    (('active_skill', 'name_en'),): ('asname',),
    (('active_skill', 'desc_en'),): ('asdesc',),
    (('series', 'name_en'),): ('seriesname',),
}
STRING_MONSTER_ATTRIBUTE_NAMES = {*sum(STRING_MONSTER_ATTRIBUTE_ALIASES.values(), ())}

BOOL_MONSTER_ATTRIBUTE_ALIASES = {}
BOOL_MONSTER_ATTRIBUTE_NAMES = {*sum(BOOL_MONSTER_ATTRIBUTE_ALIASES.values(), ())}

MONSTER_CLASS_ATTRIBUTES = {
    *sum(NUMERIC_MONSTER_ATTRIBUTE_ALIASES, ()),
    *sum(STRING_MONSTER_ATTRIBUTE_ALIASES, ()),
    *sum(BOOL_MONSTER_ATTRIBUTE_NAMES, ()),
}
MONSTER_ATTR_ALIAS_TO_ATTR_MAP = {v: k for k, vs in {
    **NUMERIC_MONSTER_ATTRIBUTE_ALIASES,
    **STRING_MONSTER_ATTRIBUTE_ALIASES,
    **BOOL_MONSTER_ATTRIBUTE_ALIASES,
}.items() for v in vs}
