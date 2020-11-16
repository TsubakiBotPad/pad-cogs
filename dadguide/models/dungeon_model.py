from .base_model import BaseModel


class DungeonModel(BaseModel):
    def __init__(self, **kwargs):
        self.dungeon_id = kwargs['dungeon_id']
        self.name_ja = kwargs['name_ja']
        self.name_en = kwargs['name_en']
        self.name_ko = kwargs['name_ko']

        self.dungeon_type = kwargs['dungeon_type']

    def to_dict(self):
        return {
            'dungeon_id': self.dungeon_id,
            'name_ja': self.name_ja,
            'name_en': self.name_en
        }
