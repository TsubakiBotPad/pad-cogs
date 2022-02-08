from .base_model import BaseModel
from .enemy_data_model import EnemyDataModel


class EncounterModel(BaseModel):
    def __init__(self, enemy_data_model: EnemyDataModel = None, **kwargs):
        self.encounter_id = kwargs['encounter_id']
        self.sub_dungeon_id = kwargs['sub_dungeon_id']
        self.enemy_id = kwargs['enemy_id']
        self.monster_id = kwargs['monster_id']
        self.stage = kwargs['stage']
        self.amount = kwargs['amount']
        self.turns = kwargs['turns']
        self.level = kwargs['level']
        self.hp = kwargs['hp']
        self.atk = kwargs['atk']
        self.defense = kwargs['defense']
        self.enemy_data = enemy_data_model

    def to_dict(self):
        return {
            'encounter_id': self.encounter_id,
            'sub_dungeon_id': self.sub_dungeon_id,
            'enemy_id': self.enemy_id,
            'monster_id': self.monster_id,
            'stage': self.stage,
            'amount': self.amount,
            'turns': self.turns,
            'level': self.level,
            'hp': self.hp,
            'atk': self.atk,
            'defense': self.defense
        }
