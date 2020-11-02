from .base_model import BaseModel
from ..database_manager import Attribute
from ..database_manager import MonsterType
from ..database_manager import enum_or_none
from ..database_manager import make_roma_subname
import tsutils


class MonsterModel(BaseModel):
    def __init__(self, **m):
        self.monster_id = m['monster_id']
        self.monster_no = self.monster_id
        self.monster_no_jp = m['monster_no_jp']
        self.monster_no_na = m['monster_no_na']
        self.monster_no_kr = m['monster_no_kr']
        self.awakenings = m['awakenings']
        self.superawakening_count = sum(int(a.is_super) for a in self.awakenings)
        self.leader_skill = m['leader_skill']
        self.active_skill = m['active_skill']
        self.series = m['series']
        self.series_id = m['series_id']
        self.name_ja = m['name_ja']
        self.name_ko = m['name_ko']
        self.name_en = m['name_en']
        self.roma_subname = None
        if self.name_en == self.name_ja:
            self.roma_subname = make_roma_subname(self.name_ja)
        else:
            # Remove annoying stuff from NA names, like Jörmungandr
            self.name_en = tsutils.rmdiacritics(self.name_en)
        self.name_en = m['name_en_override'] or self.name_en

        self.type1 = enum_or_none(MonsterType, m['type_1_id'])
        self.type2 = enum_or_none(MonsterType, m['type_2_id'])
        self.type3 = enum_or_none(MonsterType, m['type_3_id'])
        self.types = list(filter(None, [self.type1, self.type2, self.type3]))

        self.rarity = m['rarity']
        self.is_farmable = m['is_farmable']
        self.in_rem = m['in_rem']
        self.in_pem = m['in_pem']
        self.in_mpshop = m['buy_mp'] is not None
        self.buy_mp = m['buy_mp']
        self.sell_gold= m['sell_gold']
        self.sell_mp=m['sell_mp']
        self.reg_date = m['reg_date']
        self.on_jp = m['on_jp']
        self.on_na = m['on_na']
        self.on_kr = m['on_kr']
        self.attr1 = enum_or_none(Attribute, m['attribute_1_id'], Attribute.Nil)
        self.attr2 = enum_or_none(Attribute, m['attribute_2_id'], Attribute.Nil)
        self.is_equip = any([x.awoken_skill_id == 49 for x in self.awakenings])
        self.is_inheritable = m['is_inheritable']
        self.evo_gem_id = m['evo_gem_id']
        self.orb_skin_id = m['orb_skin_id']
        self.cost = m['cost']
        self.exp = m['exp']
        self.level = m['level']
        self.limit_mult = m['limit_mult']
        self.latent_slots = m['latent_slots']

        self.hp_max = m['hp_max']
        self.hp_min = m['hp_min']
        self.hp_scale = m['hp_scale']
        self.atk_max = m['atk_max']
        self.atk_min = m['atk_min']
        self.atk_scale = m['atk_scale']
        self.rcv_max = m['rcv_max']
        self.rcv_min = m['rcv_min']
        self.rcv_scale = m['rcv_scale']
        self.stat_values = {
            'hp': {'min': self.hp_min, 'max': self.hp_max, 'scale': self.hp_scale},
            'atk': {'min': self.atk_min, 'max': self.atk_max, 'scale': self.atk_scale},
            'rcv': {'min': self.rcv_min, 'max': self.rcv_max, 'scale': self.rcv_scale}
        }

        self.pronunciation_ja = m['pronunciation_ja']
        self.has_animation = m['has_animation']
        self.has_hqimage = m['has_hqimage']

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
        s_min = float(self.stat_values[key]['min'])
        s_max = float(self.stat_values[key]['max'])
        if self.level > 1:
            s_val = s_min + (s_max - s_min) * ((min(lv, self.level) - 1) / (self.level - 1)) ** self.stat_values[key]['scale']
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
