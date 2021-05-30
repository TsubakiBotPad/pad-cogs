from typing import Optional

from .base_model import BaseModel
from .enum_types import Attribute
from .enum_types import MonsterType
from .enum_types import AwakeningRestrictedLatent
from .enum_types import enum_or_none
from .active_skill_model import ActiveSkillModel
from .leader_skill_model import LeaderSkillModel
import tsutils
import re
from collections import defaultdict
import romkan

from .monster_stats import monster_stats


class MonsterModel(BaseModel):
    def __init__(self, **m):
        self.monster_id = m['monster_id']
        self.monster_no_jp = m['monster_no_jp']
        self.monster_no_na = m['monster_no_na']
        self.monster_no_kr = m['monster_no_kr']
        self.base_evo_id = m['base_evo_id']

        self.awakenings = sorted(m['awakenings'], key=lambda a: a.order_idx)
        self.superawakening_count = sum(int(a.is_super) for a in self.awakenings)
        self.leader_skill: LeaderSkillModel = m['leader_skill']
        self.leader_skill_id = self.leader_skill.leader_skill_id if self.leader_skill else None
        self.active_skill: ActiveSkillModel = m['active_skill']
        self.active_skill_id = self.active_skill.active_skill_id if self.active_skill else None

        self.series = m['series']
        self.series_id = m['series_id']
        self.name_ja = m['name_ja']
        self.name_ko = m['name_ko']
        self.name_en = self.unoverridden_name_en = m['name_en']
        self.roma_subname = None
        if self.name_en == self.name_ja:
            self.roma_subname = self.make_roma_subname(self.name_ja)
        else:
            # Remove annoying stuff from NA names, like Jörmungandr
            self.name_en = tsutils.rmdiacritics(self.name_en)
        self.name_en_override = m['name_en_override']
        self.name_en = self.name_en_override or self.name_en

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
        self.sell_gold = m['sell_gold']
        self.sell_mp = m['sell_mp']
        self.reg_date = m['reg_date']
        self.on_jp = m['on_jp']
        self.on_na = m['on_na']
        self.on_kr = m['on_kr']
        self.attr1 = enum_or_none(Attribute, m['attribute_1_id'], Attribute.Nil)
        self.attr2 = enum_or_none(Attribute, m['attribute_2_id'], Attribute.Nil)
        self.is_equip = any([x.awoken_skill_id == 49 for x in self.awakenings])
        self.is_inheritable = m['is_inheritable']
        self.is_stackable = m['is_stackable']
        self.evo_gem_id = m['evo_gem_id']
        self.orb_skin_id = m['orb_skin_id']
        self.cost = m['cost']
        self.exp = m['exp']
        self.fodder_exp = m['fodder_exp']
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

        self.voice_id_jp = m['voice_id_jp']
        self.voice_id_na = m['voice_id_na']

        self.pronunciation_ja = m['pronunciation_ja']
        self.has_animation = m['has_animation']
        self.has_hqimage = m['has_hqimage']

        self.server_priority = m['server_priority']

        self.search = MonsterSearchHelper(self)

    @property
    def killers(self):
        type_to_killers_map = {
            MonsterType.God: ['Devil'],
            MonsterType.Devil: ['God'],
            MonsterType.Machine: ['God', 'Balanced'],
            MonsterType.Dragon: ['Machine', 'Healer'],
            MonsterType.Physical: ['Machine', 'Healer'],
            MonsterType.Attacker: ['Devil', 'Physical'],
            MonsterType.Healer: ['Dragon', 'Attacker'],
        }
        if MonsterType.Balanced in self.types:
            return ['Any']
        killers = set()
        for t in self.types:
            killers.update(type_to_killers_map.get(t, []))
        return sorted(killers)

    @property
    def awakening_restricted_latents(self):
        monster_awakening_to_allowed_latent_map = [
            {27: AwakeningRestrictedLatent.UnmatchableClear},  # TPA
            {20: AwakeningRestrictedLatent.SpinnerClear},  # Bind clear
            {62: AwakeningRestrictedLatent.AbsorbPierce},  # Combo orb
        ]
        latents = []
        for row in monster_awakening_to_allowed_latent_map:
            # iterate over one thing
            for awakening in row.keys():
                if any([x.awoken_skill_id == awakening and not x.is_super for x in self.awakenings]):
                    latents.append(row[awakening])

        return latents

    @property
    def history_us(self):
        return '[{}] New Added'.format(self.reg_date)

    def awakening_count(self, awid):
        return len([x for x in self.awakenings if x.awoken_skill_id == awid])

    def stat(self, key, lv, plus=99, inherit=False, is_plus_297=True):
        return monster_stats.stat(self, key, lv, plus=plus, inherit=inherit, is_plus_297=is_plus_297)

    def stats(self, lv=99, plus=0, inherit=False):
        return monster_stats.stats(self, lv, plus=plus, inherit=inherit)

    @staticmethod
    def make_roma_subname(name_ja):
        subname = re.sub(r'[＝]', '', name_ja)
        subname = re.sub(r'[「」]', '・', subname)
        adjusted_subname = ''
        for part in subname.split('・'):
            roma_part = romkan.to_roma(part)
            if part != roma_part and not tsutils.contains_ja(roma_part):
                adjusted_subname += ' ' + roma_part.strip('-')
        return adjusted_subname.strip()

    def to_dict(self):
        return {
            'monster_id': self.monster_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en,
        }

    def get_difference(self, other):
        if self.monster_id != other.monster_id:
            raise ValueError("You cannot get the difference of monsters with different ids.")
        return MonsterDifference.from_monsters(self, other)

    def __repr__(self):
        server_prefix = self.server_priority + " " if self.server_priority != "COMBINED" else ""
        return "Monster<{}{} ({})>".format(server_prefix, self.name_en, self.monster_id)


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
    def from_monsters(cls, monster1: MonsterModel, monster2: Optional[MonsterModel]):
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


class MonsterSearchHelper:
    def __init__(self, m: MonsterModel):

        self.name = '{} {}'.format(m.name_en, m.name_ja).lower()
        leader_skill = m.leader_skill
        self.leader = leader_skill.desc.lower() if leader_skill else ''
        active_skill = m.active_skill
        self.active_name = active_skill.name.lower() if active_skill and active_skill.name else ''
        self.active_desc = active_skill.desc.lower() if active_skill and active_skill.desc else ''
        self.active = '{} {}'.format(self.active_name, self.active_desc)
        self.active_min = active_skill.turn_min if active_skill else None
        self.active_max = active_skill.turn_max if active_skill else None

        self.color = [m.attr1.name.lower()]
        self.hascolor = [c.name.lower() for c in [m.attr1, m.attr2] if c]

        self.hp, self.atk, self.rcv, self.weighted_stats = m.stats(lv=110)

        self.types = [t.name for t in m.types]

        def replace_colors(txt: str):
            return txt.replace('red', 'fire').replace('blue', 'water').replace('green', 'wood')

        self.leader = replace_colors(self.leader)
        self.active = replace_colors(self.active)
        self.active_name = replace_colors(self.active_name)
        self.active_desc = replace_colors(self.active_desc)

        self.board_change = []
        self.orb_convert = defaultdict(list)
        self.row_convert = []
        self.column_convert = []

        def color_txt_to_list(txt):
            txt = txt.replace('and', ' ')
            txt = txt.replace(',', ' ')
            txt = txt.replace('orbs', ' ')
            txt = txt.replace('orb', ' ')
            txt = txt.replace('mortal poison', 'mortalpoison')
            txt = txt.replace('jammers', 'jammer')
            txt = txt.strip()
            return txt.split()

        def strip_prev_clause(txt: str, sep: str):
            prev_clause_start_idx = txt.find(sep)
            if prev_clause_start_idx >= 0:
                prev_clause_start_idx += len(sep)
                txt = txt[prev_clause_start_idx:]
            return txt

        def strip_next_clause(txt: str, sep: str):
            next_clause_start_idx = txt.find(sep)
            if next_clause_start_idx >= 0:
                txt = txt[:next_clause_start_idx]
            return txt

        active_desc = self.active_desc
        active_desc = active_desc.replace(' rows ', ' row ')
        active_desc = active_desc.replace(' columns ', ' column ')
        active_desc = active_desc.replace(' into ', ' to ')
        active_desc = active_desc.replace('changes orbs to', 'all orbs to')

        board_change_txt = 'all orbs to'
        if board_change_txt in active_desc:
            text = strip_prev_clause(active_desc, board_change_txt)
            text = strip_next_clause(text, 'orbs')
            text = strip_next_clause(text, ';')
            self.board_change = color_txt_to_list(text)

        text = active_desc
        if 'row' in text:
            parts = re.split(r'\Wand\W|;\W', text)
            for i in range(0, len(parts)):
                if 'row' in parts[i]:
                    self.row_convert.append(strip_next_clause(
                        strip_prev_clause(parts[i], 'to '), ' orbs'))

        text = active_desc
        if 'column' in text:
            parts = re.split(r'\Wand\W|;\W', text)
            for i in range(0, len(parts)):
                if 'column' in parts[i]:
                    self.column_convert.append(strip_next_clause(
                        strip_prev_clause(parts[i], 'to '), ' orbs'))

        convert_done = self.board_change or self.row_convert or self.column_convert

        change_txt = 'change '
        if not convert_done and change_txt in active_desc and 'orb' in active_desc:
            text = active_desc
            parts = re.split(r'\Wand\W|;\W', text)
            for i in range(0, len(parts)):
                parts[i] = strip_prev_clause(parts[i], change_txt) if change_txt in parts[i] else ''

            for part in parts:
                sub_parts = part.split(' to ')
                if len(sub_parts) > 1:
                    source_orbs = color_txt_to_list(sub_parts[0])
                    dest_orbs = color_txt_to_list(sub_parts[1])
                    for so in source_orbs:
                        for do in dest_orbs:
                            self.orb_convert[so].append(do)
