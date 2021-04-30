from .base_model import BaseModel
from .awoken_skill_model import AwokenSkillModel


class AwakeningModel(BaseModel):
    """
    This class represents an awakening belonging to a monster, in contrast to AwokenSkillModel, which represents an "abstract" awoken skill.
    """

    def __init__(self, awoken_skill_model: AwokenSkillModel, **kwargs):
        self.awakening_id = kwargs['awakening_id']
        self.monster_id = kwargs['monster_id']
        self.awoken_skill_id = kwargs['awoken_skill_id']
        self.is_super = kwargs['is_super']
        self.order_idx = kwargs['order_idx']
        self.awoken_skill = awoken_skill_model
        self.name = self.awoken_skill.name

    def to_dict(self):
        return {
            'awakening_id': self.awakening_id,
        }

    def __eq__(self, other):
        if isinstance(other, AwakeningModel):
            return self.awakening_id == other.awakening_id
        elif isinstance(other, AwokenSkillModel):
            return self.awoken_skill == other
        else:
            return False
