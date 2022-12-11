from typing import List

from pydantic import BaseModel

from dbcog.models.leader_skill_model import LeaderSkillModel


class LeaderSkill(BaseModel):
    leader_skill_id: int
    name_ja: str
    name_en: str
    name_ko: str
    max_hp: int
    max_atk: int
    max_rcv: int
    max_shield: float
    max_combos: int
    bonus_damage: int
    mult_bonus_damage: int
    extra_time: int
    tags: List[int]
    desc_en: str
    desc_ja: str
    desc_ko: str

    @staticmethod
    def from_model(m: LeaderSkillModel):
        return LeaderSkill(
            leader_skill_id=m.leader_skill_id,
            name_ja=m.name_ja,
            name_en=m.name_en,
            name_ko=m.name_ko,
            max_hp=m.max_hp,
            max_atk=m.max_atk,
            max_rcv=m.max_rcv,
            max_shield=m.max_shield,
            max_combos=m.max_combos,
            bonus_damage=m.bonus_damage,
            mult_bonus_damage=m.mult_bonus_damage,
            extra_time=m.extra_time,
            tags=m.tags,
            desc_en=m.desc_en,
            desc_ja=m.desc_ja,
            desc_ko=m.desc_ko,
        )
