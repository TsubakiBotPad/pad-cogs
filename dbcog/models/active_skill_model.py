from typing import Collection, List, Optional

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

    @property
    def desc(self):
        return self.desc_en or self.desc_ja

    def to_dict(self):
        return {
            'active_part_id': self.active_part_id,
            'desc_ja': self.desc_ja,
            'desc_en': self.desc_en,
        }


class ActiveSubskillModel(BaseModel):
    def __init__(self, *, active_parts: Collection[ActivePartModel], **kwargs):
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

        self.active_parts = active_parts

    @property
    def desc(self):
        return self.desc_en or self.desc_ja

    def to_dict(self):
        return {
            'active_subskill_id': self.active_subskill_id,
            'desc_ja': self.desc_ja,
            'desc_en': self.desc_en,
        }


class ActiveSkillModel(BaseModel):
    def __init__(self, *, active_subskills: Collection[ActiveSubskillModel], **kwargs):
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

        self.turn_max = kwargs['turn_max']
        self.turn_min = kwargs['turn_min']

        self.active_subskills = active_subskills

    @property
    def desc(self):
        return self.desc_en or self.desc_ja

    @property
    def name(self):
        return self.name_en or self.name_ja

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
                   and self.turn_max == other.turn_max \
                   and self.turn_min == other.turn_min
        elif isinstance(other, ActiveSubskillModel):
            return self.active_skill_id == other.active_subskill_id \
                   and self.desc_en == other.desc_en
        elif isinstance(other, ActivePartModel):
            return self.active_skill_id == other.active_part_id \
                   and self.desc_en == other.desc_en
        return False
