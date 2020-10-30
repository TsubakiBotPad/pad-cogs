from .base_model import BaseModel
from ..database_manager import Attribute
from ..database_manager import MonsterType
from ..database_manager import enum_or_none
from ..database_manager import make_roma_subname
import tsutils


class MonsterModel(BaseModel):
    def __init__(self, **kwargs):
        self.monster_id = kwargs['monster_id']
        self.monster_no = self.monster_id
        self.monster_no_jp = kwargs['monster_no_jp']
        self.monster_no_na = kwargs['monster_no_na']
        self.monster_no_kr = kwargs['monster_no_kr']
        self.awakenings = kwargs['awakenings']
        self.leader_skill = kwargs['leader_skill']
        self.active_skill = kwargs['active_skill']
        self.series = kwargs['series']
        self.name_ja = kwargs['name_ja']
        self.name_ko = kwargs['name_ko']
        self.name_en = kwargs['name_en']
        self.roma_subname = None
        if self.name_en == self.name_ja:
            self.roma_subname = make_roma_subname(self.name_ja)
        else:
            # Remove annoying stuff from NA names, like Jörmungandr
            self.name_en = tsutils.rmdiacritics(self.name_en)
        self.name_en = kwargs['name_en_override'] or self.name_en

        self.type1 = enum_or_none(MonsterType, kwargs['type_1_id'])
        self.type2 = enum_or_none(MonsterType, kwargs['type_2_id'])
        self.type3 = enum_or_none(MonsterType, kwargs['type_3_id'])
        self.types = list(filter(None, [self.type1, self.type2, self.type3]))

        self.rarity = kwargs['rarity']
        self.is_farmable = kwargs['is_farmable']
        self.in_rem = kwargs['in_rem']
        self.in_pem = kwargs['in_pem']
        self.in_mpshop = kwargs['in_mpshop']
        self.on_jp = kwargs['on_jp']
        self.on_na = kwargs['on_na']
        self.on_kr = kwargs['on_kr']
        self.attr1 = enum_or_none(Attribute, kwargs['attribute_1_id'], Attribute.Nil)
        self.attr2 = enum_or_none(Attribute, kwargs['attribute_2_id'], Attribute.Nil)
        self.is_equip = any([x.awoken_skill_id == 49 for x in self.awakenings])

    def to_dict(self):
        return {
            'monster_id': self.monster_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en,
        }
