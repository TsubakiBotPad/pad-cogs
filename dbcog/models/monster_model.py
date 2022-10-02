import re
from typing import Set

import romkan
from tsutils.enums import Server
from tsutils.formatting import contains_ja, rmdiacritics

from .active_skill_model import ActiveSkillModel
from .base_model import BaseModel
from .enum_types import Attribute, AwakeningRestrictedLatent, MonsterType, enum_or_none
from .leader_skill_model import LeaderSkillModel
from .monster.monster_difference import MonsterDifference
from .monster_stats import monster_stats
from .series_model import SeriesModel


class MonsterModel(BaseModel):
    def __init__(self, **m):
        self.monster_id = m['monster_id']
        self.monster_no_jp = m['monster_no_jp']
        self.monster_no_na = m['monster_no_na']
        self.monster_no_kr = m['monster_no_kr']
        self.base_evo_id = m['base_evo_id']

        self.on_jp = m['on_jp']
        self.on_na = m['on_na']
        self.on_kr = m['on_kr']

        self.awakenings = sorted(m['awakenings'], key=lambda a: a.order_idx)
        self.superawakening_count = sum(int(a.is_super) for a in self.awakenings)
        self.leader_skill: LeaderSkillModel = m['leader_skill']
        self.leader_skill_id = self.leader_skill.leader_skill_id if self.leader_skill else None
        self.active_skill: ActiveSkillModel = m['active_skill']
        self.active_skill_id = self.active_skill.active_skill_id if self.active_skill else None

        self.series = m['series']
        self.all_series: Set[SeriesModel] = m['all_series']
        self.series_id = m['series_id']
        self.group_id = m['group_id']
        self.collab_id = m['collab_id']
        self.name_ja = m['name_ja']
        self.name_ko = m['name_ko']
        self.name_en = self.unoverridden_name_en = m['name_en']
        self.roma_subname = None
        if self.name_en == self.name_ja and not self.on_na:
            self.roma_subname = self.make_roma_subname(self.name_ja)
        else:
            # Remove annoying stuff from NA names, like Jörmungandr
            self.name_en = rmdiacritics(self.name_en)

        self.name_en_override = None
        # If the NA and JP names are the same, chances are the card isn't released in both reigions, and 
        # if we have an override, chances are it's JP only because we wouldn't need one for an NA only card.
        # We aren't using the on_na flag here because that flag sucks and has false positives all the time
        if self.name_en == self.name_ja:
            self.name_en_override = m['name_en_override']
        if not m['name_is_translation']:
            self.name_en_override = m['name_en_override']

        self.name_en = (self.name_en_override or self.name_en).strip()

        self.type1 = enum_or_none(MonsterType, m['type_1_id'])
        self.type2 = enum_or_none(MonsterType, m['type_2_id'])
        self.type3 = enum_or_none(MonsterType, m['type_3_id'])
        self.types = list(filter(None, [self.type1, self.type2, self.type3]))

        self.rarity = m['rarity']
        self.is_farmable = m['is_farmable']
        self.in_rem = m['in_rem']
        self.in_pem = m['in_pem']
        self.in_vem = m['in_vem']
        self.in_mpshop = m['buy_mp'] is not None
        self.buy_mp = m['buy_mp']
        self.sell_gold = m['sell_gold']
        self.sell_mp = m['sell_mp']
        self.reg_date = m['reg_date']
        self.attr1 = enum_or_none(Attribute, m['attribute_1_id'], Attribute.Nil)
        self.attr2 = enum_or_none(Attribute, m['attribute_2_id'], Attribute.Nil)
        self.is_equip = any([x.awoken_skill_id == 49 for x in self.awakenings])
        self.is_inheritable = m['is_inheritable']
        self.is_stackable = m['is_stackable']
        self.evo_gem_id = m['evo_gem_id']
        self.orb_skin_id = m['orb_skin_id']
        self.bgm_id = m['bgm_id']
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

        self.has_animation = m['has_animation']
        self.has_hqimage = m['has_hqimage']

        self.server_priority = m['server_priority']

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
    def is_material(self):
        return MonsterType.Evolve in self.types or MonsterType.Vendor in self.types or \
               MonsterType.Enhance in self.types or MonsterType.Awoken in self.types

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

    @property
    def full_damage_attr(self) -> Attribute:
        if self.attr1 == Attribute.Nil:
            return self.attr2
        return self.attr1

    @property
    def exp_curve(self) -> int:
        if self.level == 1:
            return 0
        return int(round(self.exp / ((self.level - 1) / 98) ** 2.5))

    def exp_to_level(self, target_level: int) -> int:
        return int(self.exp_curve * ((target_level - 1) / 98) ** 2.5)

    def awakening_count(self, awid):
        return len([x for x in self.awakenings if x.awoken_skill_id == awid])

    def stat(self, key, lv, plus=99, inherit=False, is_plus_297=True):
        return monster_stats.stat(self, key, lv, plus=plus, inherit=inherit, is_plus_297=is_plus_297)

    def stats(self, lv=99, plus=0, inherit=False, multiplayer: bool = False):
        return monster_stats.stats(self, lv, plus=plus, inherit=inherit, multiplayer=multiplayer)

    @staticmethod
    def make_roma_subname(name_ja):
        subname = re.sub(r'[＝]', '', name_ja)
        subname = re.sub(r'[「」]', '・', subname)
        adjusted_subname = ''
        for part in subname.split('・'):
            roma_part = romkan.to_roma(part)
            if part != roma_part and not contains_ja(roma_part):
                adjusted_subname += ' ' + roma_part.strip('-')
        return adjusted_subname.strip()

    def to_dict(self):
        return {
            'monster_id': self.monster_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en,
        }

    def get_difference(self, other):
        if other and self.monster_id != other.monster_id:
            raise ValueError("You cannot get the difference of monsters with different ids.")
        return MonsterDifference.from_monsters(self, other)

    def __repr__(self):
        server_prefix = self.server_priority.name + " " if self.server_priority != Server.COMBINED else ""
        return "Monster<{}{} ({})>".format(server_prefix, self.name_en, self.monster_id)
