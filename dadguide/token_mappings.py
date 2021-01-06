from collections import defaultdict
from enum import Enum


class Colors(Enum):
    RED = 0
    BLUE = 1
    GREEN = 2
    LIGHT = 3
    DARK = 4
    NIL = 6


COLOR_MAP = {
    Colors.RED: ('r', 'red', 'fire'),
    Colors.BLUE: ('b', 'blue', 'water'),
    Colors.GREEN: ('g', 'green', 'wood'),
    Colors.LIGHT: ('l', 'light', 'yellow'),
    Colors.DARK: ('d', 'dark', 'purple'),
    Colors.NIL: ('x', 'none', 'null', 'nil', 'white')
}

DUAL_COLOR_MAP = {}
for cid1, cns1 in COLOR_MAP.items():
    for cid2, cns2 in COLOR_MAP.items():
        ts = ()
        for t1 in cns1:
            for t2 in cns2:
                if len(t1) + len(t2) == 2:
                    ts += (t1 + t2,)
                ts += (t1 + "/" + t2,)
        DUAL_COLOR_MAP[(cid1, cid2)] = ts


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
    EQUIP = 'equip'


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
    EvoTypes.EQUIP: ('equip', 'assist')
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
    Awakenings.ENHANCEDHP: ('hp+', '+hp'),
    Awakenings.ENHANCEDATK: ('atk+', '+atk'),
    Awakenings.ENHANCEDRCV: ('rcv+', '+rcv'),
    Awakenings.REDUCERED: (),
    Awakenings.REDUCEBLUE: (),
    Awakenings.REDUCEGREEN: (),
    Awakenings.REDUCELIGHT: (),
    Awakenings.REDUCEDARK: (),
    Awakenings.AUTOHEAL: ('autoheal',),
    Awakenings.BINDRES: (),
    Awakenings.BLINDRES: (),
    Awakenings.JAMMERRES: (),
    Awakenings.POISONRES: (),
    Awakenings.ENHANCEDRED: ('oe',),
    Awakenings.ENHANCEDBLUE: ('oe',),
    Awakenings.ENHANCEDGREEN: ('oe',),
    Awakenings.ENHANCEDLIGHT: ('oe',),
    Awakenings.ENHANCEDDARK: ('oe',),
    Awakenings.EXTMOVE: ('te', 'finger'),
    Awakenings.BINDRECOVERY: (),
    Awakenings.SKILLBOOST: ('sb',),
    Awakenings.REDROW: (),
    Awakenings.BLUEROW: (),
    Awakenings.GREENROW: (),
    Awakenings.LIGHTROW: (),
    Awakenings.DARKROW: (),
    Awakenings.TPA: ('tpa', 'pronged'),
    Awakenings.SKILLBINDRES: ('sbr',),
    Awakenings.ENHANCEDHEAL: (),
    Awakenings.MULTIBOOST: ('multi',),
    Awakenings.DRAGONKILLER: (),
    Awakenings.GODKILLER: ('gk',),
    Awakenings.DEVILKILLER: ('dk',),
    Awakenings.MACHINEKILLER: ('mk',),
    Awakenings.BALANCEDKILLER: ('bk',),
    Awakenings.ATTACKERKILLER: ('ak',),
    Awakenings.PHYSICALKILLER: ('pk',),
    Awakenings.HEALERKILLER: ('hk',),
    Awakenings.EVOMATKILLER: (),
    Awakenings.AWOKENKILLER: (),
    Awakenings.FODDERKILLER: (),
    Awakenings.REDEEMKILLER: ('rk',),
    Awakenings.ENHCOMBO7C: (),
    Awakenings.GUARDBREAK: (),
    Awakenings.FUA: ('fua',),
    Awakenings.ENHTEAMHP: (),
    Awakenings.ENHTEAMRCV: (),
    Awakenings.VDP: ('vdp',),
    Awakenings.EQUIP: (),
    Awakenings.SUPERFUA: ('sfua',),
    Awakenings.SKILLCHARGE: (),
    Awakenings.UNBINDABLE: ('unbindable',),
    Awakenings.EXTMOVEPLUS: ('te+', 'finger+'),
    Awakenings.CLOUDRESIST: ('cloudres',),
    Awakenings.TAPERESIST: ('taperes',),
    Awakenings.SKILLBOOSTPLUS: ('sb+',),
    Awakenings.HP80ORMORE: ('80+', '+80'),
    Awakenings.HP50ORLESS: ('50-', '-50'),
    Awakenings.ELSHIELD: ('el',),
    Awakenings.ELATTACK: ('el',),
    Awakenings.ENHCOMBO10C: ('10c',),
    Awakenings.COMBOORB: (),
    Awakenings.VOICE: (),
    Awakenings.DUNGEONBONUS: (),
    Awakenings.REDUCEDHP: (),
    Awakenings.REDUCEDATK: (),
    Awakenings.REDUCEDRCV: (),
    Awakenings.UNBLINDABLE: (),
    Awakenings.UNJAMMABLE: (),
    Awakenings.UNPOISONABLE: (),
    Awakenings.JAMMERBLESSING: (),
    Awakenings.POISONBLESSING: (),
    Awakenings.REDCOMBOCOUNT: (),
    Awakenings.BLUECOMBOCOUNT: (),
    Awakenings.GREENCOMBOCOUNT: (),
    Awakenings.LIGHTCOMBOCOUNT: (),
    Awakenings.DARKCOMBOCOUNT: (),
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
    **DUAL_COLOR_MAP,
    **EVO_PREFIX_MAP,
    **MISC_PREFIX_MAP,
}

TOKEN_REPLACEMENTS = defaultdict(tuple, {
    'tamadra': ('tama',),
    'evolution': ('evo',),
})
