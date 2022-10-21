from .awoken_skill_model import AwokenSkillModel
from .base_model import BaseModel


class AwakeningModel(BaseModel):
    """
    This class represents an awakening belonging to a monster, in contrast to AwokenSkillModel, which represents an "abstract" awoken skill.
    """

    def __init__(self, awoken_skill_model: AwokenSkillModel, **kwargs):
        self.awakening_id: int = kwargs['awakening_id']
        self.monster_id: int = kwargs['monster_id']
        self.awoken_skill_id: int = kwargs['awoken_skill_id']
        self.is_super: int = kwargs['is_super']
        self.order_idx: int = kwargs['order_idx']
        self.awoken_skill: AwokenSkillModel = awoken_skill_model
        self.name: str = self.awoken_skill.name

    def to_dict(self):
        return {
            'awakening_id': self.awakening_id,
        }

    def __eq__(self, other):
        if isinstance(other, AwakeningModel):
            return self.awoken_skill_id == other.awoken_skill_id and self.is_super == other.is_super
        elif isinstance(other, AwokenSkillModel):
            return self.awoken_skill == other
        return False
