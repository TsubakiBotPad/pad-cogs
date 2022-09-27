from typing import List

from pydantic import BaseModel


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
