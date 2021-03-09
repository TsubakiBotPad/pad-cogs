from typing import List

from .base_model import BaseModel
from .encounter_model import EncounterModel


class SubDungeonModel(BaseModel):
    def __init__(self, **kwargs):
        self.sub_dungeon_id = kwargs['sub_dungeon_id']
        self.dungeon_id = kwargs['dungeon_id']
        self.name_ja = kwargs['name_ja']
        self.name_en = kwargs['name_en']
        self.name_ko = kwargs['name_ko']

    def to_dict(self):
        return {
            'sub_dungeon_id': self.sub_dungeon_id,
            'dungeon_id': self.dungeon_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en,
            'name_ko': self.name_ko
        }
