from typing import Any, Dict, Sequence, Union

from .base_model import BaseModel


class ActivePartModel(BaseModel):
    def __init__(self, **kwargs):
        self.active_part_id = kwargs['active_part_id']
        self.active_skill_type_id = kwargs['active_skill_type_id']

        self.desc_ja = kwargs['desc_ja']
        self.desc_en = kwargs['desc_en']
        self.desc_ko = kwargs['desc_ko']
        self.desc_templated_ja = kwargs['desc_templated_ja']
        self.desc_templated_en = kwargs['desc_templated_en']
        self.desc_templated_ko = kwargs['desc_templated_ko']

        self.desc = self.desc_en or self.desc_ja
        self.desc_templated = self.desc_templated_en or self.desc_templated_ja

    def to_dict(self):
        return {
            'active_part_id': self.active_part_id,
            'desc_ja': self.desc_ja,
            'desc_en': self.desc_en,
        }


class ActiveSubskillModel(BaseModel):
    def __init__(self, *, active_parts: Sequence[Union[ActivePartModel, Dict[str, Any]]], **kwargs):
        if active_parts and isinstance(active_parts[0], dict):
            active_parts = [ActivePartModel(**ap) for ap in active_parts]

        self.active_subskill_id = kwargs['active_subskill_id']

        self.name_ja = kwargs['name_ja']
        self.name_en = kwargs['name_en']
        self.name_ko = kwargs['name_ko']
        self.desc_ja = kwargs['desc_ja']
        self.desc_en = kwargs['desc_en']
        self.desc_ko = kwargs['desc_ko']
        self.desc_templated_ja = kwargs['desc_templated_ja']
        self.desc_templated_en = kwargs['desc_templated_en']
        self.desc_templated_ko = kwargs['desc_templated_ko']
        self.board_65 = kwargs['board_65']
        self.board_76 = kwargs['board_76']
        self.cooldown = kwargs['cooldown']

        self.active_parts = active_parts

        self.name = self.name_en or self.name_ja
        self.desc = self.desc_en or self.desc_ja
        self.desc_templated = self.desc_templated_en or self.desc_templated_ja

    def to_dict(self):
        return {
            'active_subskill_id': self.active_subskill_id,
            'desc_ja': self.desc_ja,
            'desc_en': self.desc_en,
        }


class ActiveSkillModel(BaseModel):
    def __init__(self, *, active_subskills: Sequence[Union[ActiveSubskillModel, Dict[str, Any]]], **kwargs):
        if active_subskills and isinstance(active_subskills[0], dict):
            active_subskills = [ActiveSubskillModel(**ass) for ass in active_subskills]

        self.active_skill_id = kwargs['active_skill_id']
        self.compound_skill_type_id = kwargs['compound_skill_type_id']

        self.name_ja = kwargs['name_ja']
        self.name_en = kwargs['name_en']
        self.name_ko = kwargs['name_ko']
        self.desc_ja = kwargs['desc_ja']
        self.desc_en = kwargs['desc_en']
        self.desc_ko = kwargs['desc_ko']
        self.desc_templated_ja = kwargs['desc_templated_ja']
        self.desc_templated_en = kwargs['desc_templated_en']
        self.desc_templated_ko = kwargs['desc_templated_ko']
        self.desc_official_ja = kwargs['desc_official_ja']
        self.desc_official_en = kwargs['desc_official_en']
        self.desc_official_ko = kwargs['desc_official_ko']

        self.cooldown_turns_max = kwargs['cooldown_turns_max']
        self.cooldown_turns_min = kwargs['cooldown_turns_min']

        self.active_subskills = active_subskills

        self.name = self.name_en or self.name_ja
        self.desc = self.desc_en or self.desc_ja
        self.desc_templated = self.desc_templated_en or self.desc_templated_ja

    def to_dict(self):
        return {
            'active_skill_id': self.active_skill_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en,
        }

    def __eq__(self, other):
        if isinstance(other, ActiveSkillModel):
            return self.active_skill_id == other.active_skill_id \
                   and self.desc_en == other.desc_en \
                   and self.cooldown_turns_max == other.cooldown_turns_max \
                   and self.cooldown_turns_min == other.cooldown_turns_min
        elif isinstance(other, ActiveSubskillModel):
            return self.active_skill_id == other.active_subskill_id \
                   and self.desc_en == other.desc_en
        elif isinstance(other, ActivePartModel):
            return self.active_skill_id == other.active_part_id \
                   and self.desc_en == other.desc_en
        return False
