from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class MonsterDifference:
    __slots__ = 'types', 'awakenings', 'leader_skill', 'active_skill', 'rarity', \
                'sell_gold', 'is_inheritable', 'cost', 'exp', 'fodder_exp', 'level', \
                'limit_mult', 'latent_slots', 'stat_values', 'existance'

    def __init__(self, types=False, awakenings=False, leader_skill=False, active_skill=False, rarity=False,
                 sell_gold=False, is_inheritable=False, cost=False, exp=False, fodder_exp=False, level=False,
                 limit_mult=False, latent_slots=False, stat_values=False, existance=False):
        self.types = types
        self.awakenings = awakenings
        self.leader_skill = leader_skill
        self.active_skill = active_skill
        self.rarity = rarity
        self.sell_gold = sell_gold
        self.is_inheritable = is_inheritable
        self.cost = cost
        self.exp = exp
        self.fodder_exp = fodder_exp
        self.level = level
        self.limit_mult = limit_mult
        self.latent_slots = latent_slots
        self.stat_values = stat_values
        self.existance = existance

    @classmethod
    def from_monsters(cls, monster1: "MonsterModel", monster2: Optional["MonsterModel"]):
        if monster2 is None:
            return cls(existance=True)

        return cls(
            monster1.types != monster2.types,
            monster1.awakenings != monster2.awakenings,
            monster1.leader_skill != monster2.leader_skill,
            monster1.active_skill != monster2.active_skill,
            monster1.rarity != monster2.rarity,
            monster1.sell_gold != monster2.sell_gold,
            monster1.is_inheritable != monster2.is_inheritable,
            monster1.cost != monster2.cost,
            monster1.exp != monster2.exp,
            monster1.fodder_exp != monster2.fodder_exp,
            monster1.level != monster2.level,
            monster1.limit_mult != monster2.limit_mult,
            monster1.latent_slots != monster2.latent_slots,
            monster1.stat_values != monster2.stat_values,
            False)

    @classmethod
    def from_int(cls, value: int):
        return cls(*(value & 1 << exp for exp in range(len(cls.__slots__))))

    @property
    def value(self):
        return (self.types << 0
                | self.awakenings << 1
                | self.leader_skill << 2
                | self.active_skill << 3
                | self.rarity << 4
                | self.sell_gold << 5
                | self.is_inheritable << 6
                | self.cost << 7
                | self.exp << 8
                | self.fodder_exp << 9
                | self.level << 10
                | self.limit_mult << 11
                | self.latent_slots << 12
                | self.stat_values << 13
                | self.existance << 14)

    def __bool__(self):
        return bool(self.value)

    def __repr__(self):
        vals = ', '.join(f"{value}=True" for value in self.__slots__ if getattr(self, value))
        return f"MonsterDifference({vals or 'False'})"
