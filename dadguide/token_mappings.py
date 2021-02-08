from enum import Enum

from .models.enum_types import Attribute, MonsterType

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
        ts = ()
        for t1 in cns1:
            for t2 in cns2:
                if t2 in ("white",):
                    continue
                if len(t1) + len(t2) == 2:
                    ts += (t1 + t2,)
                if (len(t1) == 1) == (len(t2) == 1):
                    ts += (t1 + "/" + t2,)
        DUAL_COLOR_MAP[(cid1, cid2)] = ts

TYPE_MAP = {
    MonsterType.Evolve: ('evolve',),
    MonsterType.Balance: ('balanced', 'bal'),
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
    EvoTypes.TRANS: ('transform', 'trans', 'transformed'),
    EvoTypes.AWOKEN: ('awoken', 'awo', 'a'),
    EvoTypes.MEGA: ('mega', 'mawoken', 'mawo', 'ma', 'megaawoken'),
    EvoTypes.REVO: ('revo', 'reincarnated', 'rv'),
    EvoTypes.SREVO: ('srevo', 'super', 'sr', 'superreincarnated'),
    EvoTypes.PIXEL: ('pixel', 'p', 'dot', 'px'),
    EvoTypes.NONPIXEL: ('nonpixel', 'np'),
}


class Awakenings(Enum):
    ENHANCEDHP = 1
    ENHANCEDATK = 2
    ENHANCEDRCV = 3
    REDUCERED = 4
    REDUCEBLUE = 5
    REDUCEGREEN = 6
    REDUCELIGHT = 7
    REDUCEDARK = 8
    AUTOHEAL = 9
    BINDRES = 10
    BLINDRES = 11
    JAMMERRES = 12
    POISONRES = 13
    ENHANCEDRED = 14
    ENHANCEDBLUE = 15
    ENHANCEDGREEN = 16
    ENHANCEDLIGHT = 17
    ENHANCEDDARK = 18
    EXTMOVE = 19
    BINDRECOVERY = 20
    SKILLBOOST = 21
    REDROW = 22
    BLUEROW = 23
    GREENROW = 24
    LIGHTROW = 25
    DARKROW = 26
    TPA = 27
    SKILLBINDRES = 28
    ENHANCEDHEAL = 29
    MULTIBOOST = 30
    DRAGONKILLER = 31
    GODKILLER = 32
    DEVILKILLER = 33
    MACHINEKILLER = 34
    BALANCEDKILLER = 35
    ATTACKERKILLER = 36
    PHYSICALKILLER = 37
    HEALERKILLER = 38
    EVOMATKILLER = 39
    AWOKENKILLER = 40
    FODDERKILLER = 41
    REDEEMKILLER = 42
    ENHCOMBO7C = 43
    GUARDBREAK = 44
    FUA = 45
    ENHTEAMHP = 46
    ENHTEAMRCV = 47
    VDP = 48
    EQUIP = 49
    SUPERFUA = 50
    SKILLCHARGE = 51
    UNBINDABLE = 52
    EXTMOVEPLUS = 53
    CLOUDRESIST = 54
    TAPERESIST = 55
    SKILLBOOSTPLUS = 56
    HP80ORMORE = 57
    HP50ORLESS = 58
    ELSHIELD = 59
    ELATTACK = 60
    ENHCOMBO10C = 61
    COMBOORB = 62
    VOICE = 63
    DUNGEONBONUS = 64
    REDUCEDHP = 65
    REDUCEDATK = 66
    REDUCEDRCV = 67
    UNBLINDABLE = 68
    UNJAMMABLE = 69
    UNPOISONABLE = 70
    JAMMERBLESSING = 71
    POISONBLESSING = 72
    REDCOMBOCOUNT = 73
    BLUECOMBOCOUNT = 74
    GREENCOMBOCOUNT = 75
    LIGHTCOMBOCOUNT = 76
    DARKCOMBOCOUNT = 77


AWOKEN_MAP = {
    Awakenings.ENHANCEDHP: ('hp+', 'hp'),
    Awakenings.ENHANCEDATK: ('atk+', 'atk'),
    Awakenings.ENHANCEDRCV: ('rcv+', 'rcv'),
    Awakenings.REDUCERED: ('elresr', 'elres'),  # element resist
    Awakenings.REDUCEBLUE: ('elresb', 'elres'),
    Awakenings.REDUCEGREEN: ('elresg', 'elres'),
    Awakenings.REDUCELIGHT: ('elresl', 'elres'),
    Awakenings.REDUCEDARK: ('elresd', 'elres'),
    Awakenings.AUTOHEAL: ('autoheal',),
    Awakenings.BINDRES: ('unbindable',),
    Awakenings.BLINDRES: ('resb',),
    Awakenings.JAMMERRES: ('resj',),
    Awakenings.POISONRES: ('resp',),
    Awakenings.ENHANCEDRED: ('oer', 'oe'),
    Awakenings.ENHANCEDBLUE: ('oeb', 'oe'),
    Awakenings.ENHANCEDGREEN: ('oeg', 'oe'),
    Awakenings.ENHANCEDLIGHT: ('oel', 'oe'),
    Awakenings.ENHANCEDDARK: ('oed', 'oe'),
    Awakenings.EXTMOVE: ('te', 'finger'),
    Awakenings.BINDRECOVERY: ('bindrcv',),
    Awakenings.SKILLBOOST: ('sb',),
    Awakenings.REDROW: ('rowr', 'row'),
    Awakenings.BLUEROW: ('rowb', 'row'),
    Awakenings.GREENROW: ('rowg', 'row'),
    Awakenings.LIGHTROW: ('rowl', 'row'),
    Awakenings.DARKROW: ('rowd', 'row'),
    Awakenings.TPA: ('tpa', 'pronged'),
    Awakenings.SKILLBINDRES: ('sbr',),
    Awakenings.ENHANCEDHEAL: ('htpa', 'oeh'),
    Awakenings.MULTIBOOST: ('multi', 'mb'),
    Awakenings.DRAGONKILLER: ('dragonkiller', 'dk', 'drk', 'killer'),
    Awakenings.GODKILLER: ('godkiller', 'gk', 'gok', 'killer'),
    Awakenings.DEVILKILLER: ('devilkiller', 'vk', 'dek', 'killer'),
    Awakenings.MACHINEKILLER: ('machinekiller', 'mk', 'mak', 'killer'),
    Awakenings.BALANCEDKILLER: ('balancedkiller', 'bk', 'bak', 'killer'),
    Awakenings.ATTACKERKILLER: ('attackerkiller', 'ak', 'aak', 'killer'),
    Awakenings.PHYSICALKILLER: ('physicalkiller', 'pk', 'phk', 'killer'),
    Awakenings.HEALERKILLER: ('healerkiller', 'hk', 'hek', 'killer'),
    Awakenings.EVOMATKILLER: ('evokiller', 'evok', 'a2killer'),
    Awakenings.AWOKENKILLER: ('awokenkiller', 'awok', 'a2killer'),
    Awakenings.FODDERKILLER: ('enhancekiller', 'enhk', 'a2killer'),
    Awakenings.REDEEMKILLER: ('vendorkiller', 'vendork', 'a2killer'),
    Awakenings.ENHCOMBO7C: ('7c',),
    Awakenings.GUARDBREAK: ('gb',),
    Awakenings.FUA: ('fua',),
    Awakenings.ENHTEAMHP: ('teamhp', 'thp'),
    Awakenings.ENHTEAMRCV: ('teamrcv', 'trcv'),
    Awakenings.VDP: ('vdp',),
    Awakenings.EQUIP: ('equip', 'assist', 'eq'),
    Awakenings.SUPERFUA: ('sfua',),
    Awakenings.SKILLCHARGE: ('rainbowhaste', 'skillcharge', 'hasteawo'),
    Awakenings.UNBINDABLE: ('unbindable',),
    Awakenings.EXTMOVEPLUS: ('te+', 'finger+'),
    Awakenings.CLOUDRESIST: ('cloudres', 'cloud'),
    Awakenings.TAPERESIST: ('taperes', 'tape'),
    Awakenings.SKILLBOOSTPLUS: ('sb+',),
    Awakenings.HP80ORMORE: ('>80', 'highhp'),
    Awakenings.HP50ORLESS: ('<50', 'lowhp'),
    Awakenings.ELSHIELD: ('elshield', 'elh', 'hel'),
    Awakenings.ELATTACK: ('el',),
    Awakenings.ENHCOMBO10C: ('10c',),
    Awakenings.COMBOORB: ('co', 'corb'),
    Awakenings.VOICE: ('voice',),
    Awakenings.DUNGEONBONUS: ('dgbonus', 'dgboost'),
    Awakenings.REDUCEDHP: ('hp-',),
    Awakenings.REDUCEDATK: ('atk-',),
    Awakenings.REDUCEDRCV: ('rcv-',),
    Awakenings.UNBLINDABLE: ('resb+', 'b+',),
    Awakenings.UNJAMMABLE: ('resj+', 'j+',),
    Awakenings.UNPOISONABLE: ('resp+', 'p+',),
    Awakenings.JAMMERBLESSING: ('jblessing', 'sfj', 'jsurge'),
    Awakenings.POISONBLESSING: ('pblessing', 'sfp', 'psurge'),
    Awakenings.REDCOMBOCOUNT: ('ccr', 'cc'),
    Awakenings.BLUECOMBOCOUNT: ('ccb', 'cc'),
    Awakenings.GREENCOMBOCOUNT: ('ccg', 'cc'),
    Awakenings.LIGHTCOMBOCOUNT: ('ccl', 'cc'),
    Awakenings.DARKCOMBOCOUNT: ('ccd', 'cc'),
}


class MiscModifiers(Enum):
    CHIBI = 'Chibi'
    STORY = 'Story'
    FARMABLE = 'Farmable'
    REM = 'REM'
    MP = 'MP'
    INJP = 'In JP Server'
    ONLYJP = 'Only in JP Server'
    INNA = 'In NA Server'
    ONLYNA = 'Only in NA Server'
    REGULAR = 'Metaseries: REGULAR'
    EVENT = 'Metaseries: Event'
    SEASONAL = 'Metaseries: Seasonal'
    COLLAB = 'Metaseries: Collab'


MISC_MAP = {
    MiscModifiers.CHIBI: ('chibi', 'mini'),
    MiscModifiers.STORY: ('story',),
    MiscModifiers.FARMABLE: ('farmable',),
    MiscModifiers.REM: ('rem',),
    MiscModifiers.MP: ('mp',),
    MiscModifiers.INJP: ('injp',),
    MiscModifiers.INNA: ('inna',),
    MiscModifiers.ONLYJP: ('jp',),
    MiscModifiers.ONLYNA: ('na',),
    MiscModifiers.REGULAR: ('regular',),
    MiscModifiers.EVENT: ('event',),
    MiscModifiers.SEASONAL: ('seasonal',),
    MiscModifiers.COLLAB: ('collab',)
}

MULTI_WORD_TOKENS = {tuple(ts.split()) for ts in {
    'super reincarnated',
    'mega awoken'
}}

KNOWN_MODIFIERS = {v for vs in {
    *COLOR_MAP.values(),
    *SUB_COLOR_MAP.values(),
    *DUAL_COLOR_MAP.values(),
    *TYPE_MAP.values(),
    *AWOKEN_MAP.values(),
    *EVO_MAP.values(),
    *MISC_MAP.values(),
} for v in vs}

COLOR_TOKENS = {
    *sum(COLOR_MAP.values(), ()),
    *sum(SUB_COLOR_MAP.values(), ()),
    *sum(DUAL_COLOR_MAP.values(), ()),
}

AWAKENING_TOKENS = {*sum(AWOKEN_MAP.values(), ())}
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

HAZARDOUS_IN_NAME_PREFIXES = {
    "reincarnated"
}
