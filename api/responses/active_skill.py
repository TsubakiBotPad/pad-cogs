from typing import List

from pydantic import BaseModel

from dbcog.models.active_skill_model import ActiveSkillModel, ActiveSubskillModel, ActivePartModel


class ActivePart(BaseModel):
    active_part_id: int
    active_skill_type_id: int
    desc_ja: str
    desc_en: str
    desc_ko: str
    desc_templated_ja: str
    desc_templated_en: str
    desc_templated_ko: str
    desc: str
    desc_templated: str

    @staticmethod
    def from_model(m: ActivePartModel):
        return ActivePart(
            active_part_id=m.active_part_id,
            active_skill_type_id=m.active_skill_type_id,
            desc_ja=m.desc_ja,
            desc_en=m.desc_en,
            desc_ko=m.desc_ko,
            desc_templated_ja=m.desc_templated_ja,
            desc_templated_en=m.desc_templated_en,
            desc_templated_ko=m.desc_templated_ko,
            desc=m.desc,
            desc_templated=m.desc_templated,
        )


class ActiveSubskill(BaseModel):
    active_subskill_id: int
    name_ja: str
    name_en: str
    name_ko: str
    desc_ja: str
    desc_en: str
    desc_ko: str
    desc_templated_ja: str
    desc_templated_en: str
    desc_templated_ko: str
    board_65: str
    board_76: str
    cooldown: int
    active_parts: List[ActivePart]
    name: str
    desc: str
    desc_templated: str

    @staticmethod
    def from_model(m: ActiveSubskillModel):
        return ActiveSubskill(
            active_subskill_id=m.active_subskill_id,
            name_ja=m.name_ja,
            name_en=m.name_en,
            name_ko=m.name_ko,
            desc_ja=m.desc_ja,
            desc_en=m.desc_en,
            desc_ko=m.desc_ko,
            desc_templated_ja=m.desc_templated_ja,
            desc_templated_en=m.desc_templated_en,
            desc_templated_ko=m.desc_templated_ko,
            board_65=m.board_65,
            board_76=m.board_76,
            cooldown=m.cooldown,
            active_parts=[ActivePart.from_model(a) for a in m.active_parts],
            name=m.name,
            desc=m.desc,
            desc_templated=m.desc_templated,
        )


class ActiveSkill(BaseModel):
    active_skill_id: int
    compound_skill_type_id: int
    name_ja: str
    name_en: str
    name_ko: str
    desc_ja: str
    desc_en: str
    desc_ko: str
    desc_templated_ja: str
    desc_templated_en: str
    desc_templated_ko: str
    desc_official_ja: str
    desc_official_en: str
    desc_official_ko: str
    cooldown_turns_max: int
    cooldown_turns_min: int
    active_subskills: List[ActiveSubskill]
    name: str
    desc: str
    desc_templated: str

    @staticmethod
    def from_model(m: ActiveSkillModel):
        return ActiveSkill(
            active_skill_id=m.active_skill_id,
            compound_skill_type_id=m.compound_skill_type_id,
            name_ja=m.name_ja,
            name_en=m.name_en,
            name_ko=m.name_ko,
            desc_ja=m.desc_ja,
            desc_en=m.desc_en,
            desc_ko=m.desc_ko,
            desc_templated_ja=m.desc_templated_ja,
            desc_templated_en=m.desc_templated_en,
            desc_templated_ko=m.desc_templated_ko,
            desc_official_ja=m.desc_official_ja,
            desc_official_en=m.desc_official_en,
            desc_official_ko=m.desc_official_ko,
            cooldown_turns_max=m.cooldown_turns_max,
            cooldown_turns_min=m.cooldown_turns_min,
            active_subskills=[ActiveSubskill.from_model(a) for a in m.active_subskills],
            name=m.name,
            desc=m.desc,
            desc_templated=m.desc_templated,
        )
