from typing import TYPE_CHECKING

from pydantic import BaseModel

from api.responses.awoken_skill import AwokenSkill

if TYPE_CHECKING:
    from dbcog.models.awakening_model import AwakeningModel


class Awakening(BaseModel):
    monster_id: int
    awoken_skill_id: int
    is_super: int
    order_idx: int
    awoken_skill: AwokenSkill
    name: str

    @staticmethod
    def from_model(m: "AwakeningModel"):
        return Awakening(
            monster_id=m.monster_id,
            awoken_skill_id=m.awoken_skill_id,
            is_super=m.is_super,
            order_idx=m.order_idx,
            awoken_skill=AwokenSkill.from_model(m.awoken_skill),
            name=m.name,
        )
