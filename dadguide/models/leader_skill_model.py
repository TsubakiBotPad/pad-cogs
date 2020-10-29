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
        self.desc_en = kwargs['desc_en']
        self.desc_ja = kwargs['desc_ja']
        self.desc_ko = kwargs['desc_ko']

    @property
    def data(self):
        return self.max_hp, self.max_atk, self.max_rcv, self.max_shield

    @property
    def desc(self):
        return self.desc_en or self.desc_ja

    @property
    def name(self):
        return self.name_en or self.name_ja

    def to_dict(self):
        return {
            'monster_id': self.leader_skill_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en,
        }
