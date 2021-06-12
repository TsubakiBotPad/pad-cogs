import re

from .base_model import BaseModel


class LeaderSkillModel(BaseModel):
    def __init__(self, **kwargs):
        self.leader_skill_id = kwargs['leader_skill_id']
        self.name_ja = kwargs['name_ja']
        self.name_en = kwargs['name_en']
        self.name_ko = kwargs['name_ko']
        self.max_hp = kwargs['max_hp']
        self.max_atk = kwargs['max_atk']
        self.max_rcv = kwargs['max_rcv']
        self.max_shield = kwargs['max_shield']
        self.max_combos = kwargs['max_combos']
        self.bonus_damage = kwargs['bonus_damage']
        self.mult_bonus_damage = kwargs['mult_bonus_damage']
        self.extra_time = kwargs['extra_time']
        self.tags = [int(tag) for tag in re.findall(r'\((\d+)\)', kwargs['tags'])]
        self.desc_en = kwargs['desc_en']
        self.desc_ja = kwargs['desc_ja']
        self.desc_ko = kwargs['desc_ko']

    @property
    def data(self):
        return (self.max_hp,
                self.max_atk,
                self.max_rcv,
                self.max_shield,
                self.max_combos,
                self.bonus_damage,
                self.mult_bonus_damage,
                self.extra_time)

    @property
    def desc(self):
        return self.desc_en or self.desc_ja

    @property
    def name(self):
        return self.name_en or self.name_ja

    @property
    def is_7x6(self):
        return 200 in self.tags

    def to_dict(self):
        return {
            'leader_skill_id': self.leader_skill_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en,
        }

    def __eq__(self, other):
        if isinstance(other, LeaderSkillModel):
            return self.leader_skill_id == other.leader_skill_id \
                   and self.data == other.data \
                   and self.desc_en == other.desc_en
        return False
