from pydantic import BaseModel

from api.responses.awoken_skill import AwokenSkill


class Awakening(BaseModel):
    awakening_id: int
    monster_id: int
    awoken_skill_id: int
    is_super: int
    order_idx: int
    awoken_skill: AwokenSkill
    name: str
