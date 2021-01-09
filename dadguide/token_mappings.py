from collections import defaultdict
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

SUB_COLOR_MAP = {k: tuple('?'+t for t in v) for k, v in COLOR_MAP.items()}

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
    MonsterType.Awoken: ('awoken',),
    MonsterType.Enhance: ('enhance', 'fodder', 'enh'),
    MonsterType.Vendor: ('vendor', 'redeemable'),
}


class EvoTypes(Enum):
    BASE = 'base'
    EVO = 'evolved'
    UVO = 'ulimate'
    UUVO = 'super ultimate'
    TRANS = 'transform'
    AWOKEN = 'awoken'
    MEGA = 'mega awoken'
    REVO = 'reincarnated'
    SREVO = 'super reincarnated'
    PIXEL = 'pixel'
    NONPIXEL = 'nonpixel'


EVO_PREFIX_MAP = {
    EvoTypes.BASE: ('base',),
    EvoTypes.EVO: ('evo', 'evolved'),
    EvoTypes.UVO: ('uvo', 'ult', 'ultimate', 'uevo'),
    EvoTypes.UUVO: ('uuvo', 'uult', 'uultimate', 'uuevo', 'suvo'),
    EvoTypes.TRANS: ('transform', 'trans', 'transformed'),
    EvoTypes.AWOKEN: ('awoken', 'awo', 'a'),
    EvoTypes.MEGA: ('mega', 'mawoken', 'mawo', 'ma', 'mega awoken'),
    EvoTypes.REVO: ('revo', 'reincarnated'),
    EvoTypes.SREVO: ('srevo', 'super', 'sr', 'super reincarnated'),
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


AWOKEN_PREFIX_MAP = {
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
    Awakenings.DRAGONKILLER: ('dk', 'drk', 'killer'),
    Awakenings.GODKILLER: ('gk', 'gok', 'killer'),
    Awakenings.DEVILKILLER: ('vk', 'dek', 'killer'),
    Awakenings.MACHINEKILLER: ('mk', 'mak', 'killer'),
    Awakenings.BALANCEDKILLER: ('bk', 'bak', 'killer'),
    Awakenings.ATTACKERKILLER: ('ak', 'aak', 'killer'),
    Awakenings.PHYSICALKILLER: ('pk', 'phk', 'killer'),
    Awakenings.HEALERKILLER: ('hk', 'hek', 'killer'),
    Awakenings.EVOMATKILLER: ('evok', 'a2killer'),
    Awakenings.AWOKENKILLER: ('awok', 'a2killer'),
    Awakenings.FODDERKILLER: ('enhk', 'a2killer'),
    Awakenings.REDEEMKILLER: ('vendork', 'a2killer'),
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
    Awakenings.REDCOMBOCOUNT: ('ccr',),
    Awakenings.BLUECOMBOCOUNT: ('ccb',),
    Awakenings.GREENCOMBOCOUNT: ('ccg',),
    Awakenings.LIGHTCOMBOCOUNT: ('ccl',),
    Awakenings.DARKCOMBOCOUNT: ('ccd',),
}


class MiscPrefixes(Enum):
    CHIBI = 'chibi'
    NONCHIBI = 'nonchibi'
    FARMABLE = 'farmable'


MISC_PREFIX_MAP = {
    MiscPrefixes.CHIBI: ('chibi', 'mini'),
    MiscPrefixes.NONCHIBI: ('nonchibi', 'nc'),
    MiscPrefixes.FARMABLE: ('farmable', 'nrem')
}

PREFIX_MAPS = {
    **COLOR_MAP,
    **TYPE_MAP,
    **DUAL_COLOR_MAP,
    **EVO_PREFIX_MAP,
    **MISC_PREFIX_MAP,
}

TOKEN_REPLACEMENTS = defaultdict(tuple, {
    'tamadra': ('tama',),
    'evolution': ('evo',),
})
