from collections import defaultdict
from enum import Enum


class Colors(Enum):
    RED = 0
    BLUE = 1
    GREEN = 2
    LIGHT = 3
    DARK = 4
    NIL = 6


COLOR_MAP = {Colors.RED: ('r', 'red', 'fire'),
             Colors.BLUE: ('b', 'blue', 'water'),
             Colors.GREEN: ('g', 'green', 'wood'),
             Colors.LIGHT: ('l', 'light', 'yellow'),
             Colors.DARK: ('d', 'dark', 'purple'),
             Colors.NIL: ('x', 'none', 'null', 'nil', 'white')}


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


EVO_PREFIX_MAP = {EvoTypes.BASE: ('base',),
                  EvoTypes.EVO: ('evo', 'evolved'),
                  EvoTypes.UVO: ('uvo', 'ult', 'ultimate', 'uevo'),
                  EvoTypes.UUVO: ('uuvo', 'uult', 'uultimate', 'uuevo'),
                  EvoTypes.TRANS: ('transform', 'trans', 'transformed'),
                  EvoTypes.AWOKEN: ('awoken', 'awo', 'a'),
                  EvoTypes.MEGA: ('mega', 'mawoken', 'mawo', 'ma', 'mega awoken'),
                  EvoTypes.REVO: ('revo', 'reincarnated'),
                  EvoTypes.SREVO: ('srevo', 'super', 'sr', 'super reincarnated'),
                  EvoTypes.PIXEL: ('pixel', 'p', 'dot', 'px'),
                  EvoTypes.NONPIXEL: ('nonpixel', 'np'),
                  EvoTypes.EQUIP: ('equip', 'assist')}


class MiscPrefixes(Enum):
    CHIBI = 'chibi'
    NONCHIBI = 'nonchibi'
    FARMABLE = 'farmable'


MISC_PREFIX_MAP = {MiscPrefixes.CHIBI: ('chibi', 'mini'),
                   MiscPrefixes.NONCHIBI: ('nonchibi', 'nc'),
                   MiscPrefixes.FARMABLE: ('farmable', 'nrem')}

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
