from .base_model import BaseModel


class AwokenSkillModel(BaseModel):
    def __init__(self, **kwargs):
        self.awoken_skill_id = kwargs['awoken_skill_id']
        self.name_ja = kwargs['name_ja']
        self.name_en = kwargs['name_en']
        self.name_ko = kwargs['name_ko']
        self.name = self.name_en if self.name_en is not None else self.name_ja
        self.desc_ja = kwargs['name_ja']
        self.desc_en = kwargs['desc_en']
        self.desc_ja = kwargs['desc_ja']
        self.desc_ko = kwargs['desc_ko']
        self.adj_hp = kwargs['adj_hp']
        self.adj_atk = kwargs['adj_atk']
        self.adj_rcv = kwargs['adj_rcv']

    def to_dict(self):
        return {
            'awoken_skill_id': self.awoken_skill_id,
            'name_en': self.name_en,
        }

    def __eq__(self, other):
        if hasattr(other, "awoken_skill"):
            return self == other.awoken_skill
        elif hasattr(other, "awoken_skill_id"):
            return self.awoken_skill_id == other.awoken_skill_id
        else:
            return False
