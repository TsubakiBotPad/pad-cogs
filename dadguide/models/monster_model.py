from .base_model import BaseModel
from ..database_manager import Attribute
from ..database_manager import MonsterType
from ..database_manager import enum_or_none
from ..database_manager import make_roma_subname
import tsutils


class MonsterModel(BaseModel):
    def __init__(self, **kwargs):
        self.monster_id = kwargs['monster_id']
        self.monster_no = self.monster_id
        self.monster_no_jp = kwargs['monster_no_jp']
        self.monster_no_na = kwargs['monster_no_na']
        self.monster_no_kr = kwargs['monster_no_kr']
        self.awakenings = kwargs['awakenings']
        self.leader_skill = kwargs['leader_skill']
        self.active_skill = kwargs['active_skill']
        self.series = kwargs['series']
        self.name_ja = kwargs['name_ja']
        self.name_ko = kwargs['name_ko']
        self.name_en = kwargs['name_en']
        self.roma_subname = None
        if self.name_en == self.name_ja:
            self.roma_subname = make_roma_subname(self.name_ja)
        else:
            # Remove annoying stuff from NA names, like Jörmungandr
            self.name_en = tsutils.rmdiacritics(self.name_en)
        self.name_en = kwargs['name_en_override'] or self.name_en

        self.type1 = enum_or_none(MonsterType, kwargs['type_1_id'])
        self.type2 = enum_or_none(MonsterType, kwargs['type_2_id'])
        self.type3 = enum_or_none(MonsterType, kwargs['type_3_id'])
        self.types = list(filter(None, [self.type1, self.type2, self.type3]))

        self.rarity = kwargs['rarity']
        self.is_farmable = kwargs['is_farmable']
        self.in_rem = kwargs['in_rem']
        self.in_pem = kwargs['in_pem']
        self.in_mpshop = kwargs['buy_mp'] is not None
        self.reg_date = kwargs['reg_date']
        self.on_jp = kwargs['on_jp']
        self.on_na = kwargs['on_na']
        self.on_kr = kwargs['on_kr']
        self.attr1 = enum_or_none(Attribute, kwargs['attribute_1_id'], Attribute.Nil)
        self.attr2 = enum_or_none(Attribute, kwargs['attribute_2_id'], Attribute.Nil)
        self.is_equip = any([x.awoken_skill_id == 49 for x in self.awakenings])
        self.is_inheritable = kwargs['is_inheritable']
        self.evo_gem_id = kwargs['evo_gem_id']

    @property
    def killers(self):
        type_to_killers_map = {
            MonsterType.God: ['Devil'],
            MonsterType.Devil: ['God'],
            MonsterType.Machine: ['God', 'Balance'],
            MonsterType.Dragon: ['Machine', 'Healer'],
            MonsterType.Physical: ['Machine', 'Healer'],
            MonsterType.Attacker: ['Devil', 'Physical'],
            MonsterType.Healer: ['Dragon', 'Attacker'],
        }
        if MonsterType.Balance in self.types:
            return ['Any']
        killers = set()
        for t in self.types:
            killers.update(type_to_killers_map.get(t, []))
        return sorted(killers)

    @property
    def history_us(self):
        return '[{}] New Added'.format(self.reg_date)

    def stat(self, key, lv, plus=99, inherit=False, is_plus_297=True):
        s_min = float(self[key + '_min'])
        s_max = float(self[key + '_max'])
        if self.level > 1:
            s_val = s_min + (s_max - s_min) * ((min(lv, self.level) - 1) / (self.level - 1)) ** self[key + '_scale']
        else:
            s_val = s_min
        if lv > 99:
            s_val *= 1 + (self.limit_mult / 11 * (lv - 99)) / 100
        plus_dict = {'hp': 10, 'atk': 5, 'rcv': 3}
        s_val += plus_dict[key] * max(min(plus, 99), 0)
        if inherit:
            inherit_dict = {'hp': 0.10, 'atk': 0.05, 'rcv': 0.15}
            if not is_plus_297:
                s_val -= plus_dict[key] * max(min(plus, 99), 0)
            s_val *= inherit_dict[key]
        return int(round(s_val))

    def stats(self, lv=99, plus=0, inherit=False):
        is_plus_297 = False
        if plus == 297:
            plus = (99, 99, 99)
            is_plus_297 = True
        elif plus == 0:
            plus = (0, 0, 0)
        hp = self.stat('hp', lv, plus[0], inherit, is_plus_297)
        atk = self.stat('atk', lv, plus[1], inherit, is_plus_297)
        rcv = self.stat('rcv', lv, plus[2], inherit, is_plus_297)
        weighted = int(round(hp / 10 + atk / 5 + rcv / 3))
        return hp, atk, rcv, weighted

    def to_dict(self):
        return {
            'monster_id': self.monster_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en,
        }
