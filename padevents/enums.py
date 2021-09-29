from enum import Enum, auto


class EventLength(Enum):
    limited = auto()
    daily = auto()
    weekly = auto()
    special = auto()


class DungeonType(Enum):
    Unknown = -1
    Normal = 0
    Special = 1
    Technical = 2
    SoloSpecial = 3
    Tournament = 4
    ThreePlayer = 7
    Story = 9
    EightPlayer = 10
