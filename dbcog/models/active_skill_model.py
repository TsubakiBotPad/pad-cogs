from .base_model import BaseModel


class ActiveSkillModel(BaseModel):
    def __init__(self, **kwargs):
        self.active_skill_id = kwargs['active_skill_id']
        self.name_ja = kwargs['name_ja']
        self.name_en = kwargs['name_en']
        self.name_ko = kwargs['name_ko']

        self.desc_ja = kwargs['desc_ja']
        self.desc_en = kwargs['desc_en']
        self.desc_ko = kwargs['desc_ko']

        self.turn_max = kwargs['turn_max']
        self.turn_min = kwargs['turn_min']

    @property
    def desc(self):
        return self.desc_en or self.desc_ja

    @property
    def name(self):
        return self.name_en or self.name_ja

    def to_dict(self):
        return {
            'monster_id': self.active_skill_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en,
        }

    def __eq__(self, other):
        if isinstance(other, ActiveSkillModel):
            return self.active_skill_id == other.active_skill_id \
                   and self.desc_en == other.desc_en \
                   and self.turn_max == other.turn_max \
                   and self.turn_min == other.turn_min
        return False
