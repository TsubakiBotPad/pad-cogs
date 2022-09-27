from typing import List

from pydantic import BaseModel


class LeaderSkill(BaseModel):
    leader_skill_id: int
    name_ja: str
    name_en: str
    name_ko: str
    max_hp: int
    max_atk: int
    max_rcv: int
    max_shield: int
    max_combos: int
    bonus_damage: int
    mult_bonus_damage: int
    extra_time: int
    tags: List[int]
    desc_en: str
    desc_ja: str
    desc_ko: str
