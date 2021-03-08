from .base_model import BaseModel


class EnemySkillModel(BaseModel):
    def __init__(self, **kwargs):
        self.enemy_skill_id = kwargs['enemy_skill_id']
        self.name_en = kwargs['name_en']
        self.desc_en = kwargs['desc_en']
        self.desc_en_emoji = kwargs['desc_en_emoji']
        self.min_hits = kwargs['min_hits']
        self.max_hits = kwargs['max_hits']
        self.atk_mult = kwargs['atk_mult']


    def to_dict(self):
        return {
            'enemy_skill_id': self.enemy_skill_id,
            'name_en': self.name_en,
            'desc_en': self.desc_en,
            'desc_en_emoji': self.desc_en_emoji,
            'min_hits': self.min_hits,
            'max_hits': self.max_hits,
            'atk_mult': self.atk_mult
        }
