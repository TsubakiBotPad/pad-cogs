from collections import defaultdict
from enum import Enum


COLOR_MAP = {0: ('r', 'red', 'fire'),
             1: ('b', 'blue', 'water'),
             2: ('g', 'green', 'wood'),
             3: ('l', 'light', 'yellow'),
             4: ('d', 'dark', 'purple'),
             6: ('x', 'none', 'null', 'nil', 'white')}


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
                  EvoTypes.PIXEL: ('pixel', 'p', 'dot'),
                  EvoTypes.NONPIXEL: ('nonpixel', 'np'),
                  EvoTypes.EQUIP: ('equip', 'assist')}


class MiscPrefixes(Enum):
    CHIBI = 'chibi'
    NONCHIBI = 'nonchibi'
    FARMABLE = 'farmable'


MISC_PREFIX_MAP = {MiscPrefixes.CHIBI: ('chibi', 'mini'),
                   MiscPrefixes.NONCHIBI: ('nonchibi', 'nc'),
                   MiscPrefixes.FARMABLE: ('farmable', 'nrem')}

PREFIX_MAPS = [
    COLOR_MAP,
    EVO_PREFIX_MAP,
    MISC_PREFIX_MAP,
]

TOKEN_REPLACEMENTS = defaultdict(tuple, {
    'tamadra': ('tama',),
    'evolution': ('evo',),
})
