from enum import Enum

from tsutils.enums import Server


class Attribute(Enum):
    """Standard 5 PAD colors in enum form. Values correspond to DadGuide values."""
    Fire = 0
    Water = 1
    Wood = 2
    Light = 3
    Dark = 4
    Unknown = 5
    Nil = 6


class MonsterType(Enum):
    Evolve = 0
    Balanced = 1
    Physical = 2
    Healer = 3
    Dragon = 4
    God = 5
    Attacker = 6
    Devil = 7
    Machine = 8
    Awoken = 12
    Enhance = 14
    Vendor = 15


class InternalEvoType(Enum):
    """Evo types unsupported by DadGuide."""
    Base = "Base"
    Normal = "Normal"
    Ultimate = "Ultimate"
    Reincarnated = "Reincarnated"
    Assist = "Assist"
    Pixel = "Pixel"
    SuperReincarnated = "Super Reincarnated"


class AwakeningRestrictedLatent(Enum):
    """Latent awakenings with availability gated by having an awakening"""
    UnmatchableClear = 606
    SpinnerClear = 607
    AbsorbPierce = 608


def enum_or_none(enum, value, default=None):
    if value is not None:
        return enum(value)
    else:
        return default


DEFAULT_SERVER = Server.COMBINED
SERVERS = [Server.COMBINED, Server.NA]


class AwokenSkills(Enum):
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
    CROSSATTACK = 78
    ATTR3BOOST = 79
    ATTR4BOOST = 80
    ATTR5BOOST = 81
    BLOBBOOST = 82
    ADDTYPEDRAGON = 83
    ADDTYPEGOD = 84
    ADDTYPEDEVIL = 85
    ADDTYPEMACHINE = 86
    ADDTYPEBALANCED = 87
    ADDTYPEATTACKER = 88
    ADDTYPEPHYSICAL = 89
    ADDTYPEHEALER = 90
    SUBATTRRED = 91
    SUBATTRBLUE = 92
    SUBATTRGREEN = 93
    SUBATTRLIGHT = 94
    SUBATTRDARK = 95
    TPAPLUS = 96
    SKILLCHARGEPLUS = 97
    AUTOHEALPLUS = 98
    ENHANCEDREDPLUS = 99
    ENHANCEDBLUEPLUS = 100
    ENHANCEDGREENPLUS = 101
    ENHANCEDLIGHTPLUS = 102
    ENHANCEDDARKPLUS = 103
    ENHANCEDHEALPLUS = 104
